from qgis.core import QgsProject, QgsExpressionContextUtils, QgsApplication, QgsAuthMethodConfig
from PyQt5.QtCore import QTimer
import psycopg2
import json
import os

# Globaalit muuttujat
update_timer = None
last_state = None

def load_api_credentials():
    """Lataa API-avaimet PostgreSQL-kannasta ja tallentaa QGIS auth manageriin"""
    try:
        conn = psycopg2.connect(service='jkr')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'jkr_qgis_projektit'
                AND table_name = 'qgis_api_credentials'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("jkr_qgis_projektit.qgis_api_credentials taulua ei löydy - ohitetaan API-avainten lataus")
            cursor.close()
            conn.close()
            return
        
        cursor.execute("""
            SELECT auth_id, service_name, auth_type, auth_config 
            FROM jkr_qgis_projektit.qgis_api_credentials
            ORDER BY auth_id ASC
        """)
        
        auth_manager = QgsApplication.authManager()
        
        if not auth_manager.masterPasswordHashInDatabase():
            master_pw = os.getenv('QGIS_MASTER_PASSWORD', 'jatehuolto_master')
            auth_manager.setMasterPassword(master_pw, True)
        
        credentials_loaded = 0
        
        for auth_id, service_name, auth_type, auth_config in cursor.fetchall():
            config_data = json.loads(auth_config) if isinstance(auth_config, str) else auth_config
            
            auth_cfg = QgsAuthMethodConfig()
            auth_cfg.setId(auth_id)  # TÄMÄ on se ID joka näkyy QGIS:ssä!
            auth_cfg.setName(service_name)
            
            if auth_type == 'basic':
                auth_cfg.setMethod('Basic')
                auth_cfg.setConfig('username', config_data.get('username', ''))
                auth_cfg.setConfig('password', config_data.get('password', ''))
            
            elif auth_type == 'apikey':
                auth_cfg.setMethod('Basic')
                auth_cfg.setConfig('username', config_data.get('key', ''))
                auth_cfg.setConfig('password', '')
            
            elif auth_type == 'bearer':
                auth_cfg.setMethod('Basic')
                auth_cfg.setConfig('username', 'Bearer')
                auth_cfg.setConfig('password', config_data.get('token', ''))
            
            # Tallenna tai päivitä
            if auth_id in auth_manager.configIds():
                auth_manager.updateAuthenticationConfig(auth_cfg)
            else:
                auth_manager.storeAuthenticationConfig(auth_cfg)
            
            credentials_loaded += 1
        
        cursor.close()
        conn.close()
        
        if credentials_loaded > 0:
            print(f"✓ Ladattiin {credentials_loaded} API-credential(ia) kannasta")
        
    except Exception as e:
        print(f"Virhe API-avainten latauksessa: {e}")

def openProject():
    """Ajetaan kun projekti avataan"""
    global update_timer, last_state
    
    # UUSI: Lataa API-avaimet ensimmäisenä
    load_api_credentials()
    
    def update_filters():
        """Päivittää velvoitelayerit Kohteet-layerin rule-valintojen perusteella"""
        global last_state
        
        try:
            # Hae Kohteet-layer
            kohteet_layers = QgsProject.instance().mapLayersByName('Kohteet')
            if not kohteet_layers:
                return
            
            kohteet_layer = kohteet_layers[0]
            renderer = kohteet_layer.renderer()
            
            if renderer.type() != 'RuleRenderer':
                return
            
            # Kerää aktiiviset kohdetyyppi_id:t
            active_ids = []
            root_rule = renderer.rootRule()
            
            for rule in root_rule.children():
                if rule.active():
                    filter_exp = rule.filterExpression()
                    # Parsitaan kohdetyyppi_id arvo filteristä
                    if 'kohdetyyppi_id' in filter_exp:
                        try:
                            parts = filter_exp.split('=')
                            if len(parts) == 2:
                                id_str = parts[1].strip().strip('"').strip("'")
                                active_ids.append(id_str)
                        except:
                            pass

            # Kuljetus ja kompostori layerit
            kuljetus_kompostori_layers = {
                'Kuljetustiedot jätelajeittain': None,
                'Kompostointi': None # Ei kompostori rajausta
            }
            
            # Tarkista velvoitelayereiden näkyvyys
            velvoite_layers = {
                'Sekajätevelvoitteet': (3,4,5,6,7,8,9,10,11,12,30),
                'Biojätevelvoitteet': (13,14,15,16,17,44,45,46,47,48),
                'Muovivelvoitteet': (18,19,20),
                'Kartonkivelvoitteet': (21,22,23),
                'Lasipakkausvelvoitteet': (24,25,26),
                'Metallivelvoitteet': (27,28,29),
                'Lietevelvoite': (31,32,33,34,35,36,37,38,39,40,41,42,43),
                'Velvoiteyhteenvedot': None  # Ei velvoitemalli_id rajausta
            }
            
            any_velvoite_active = False
            
            for layer_name in {**velvoite_layers, **kuljetus_kompostori_layers}.keys():
                layers = QgsProject.instance().mapLayersByName(layer_name)
                if layers:
                    layer = layers[0]
                    tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
                    if tree_layer and tree_layer.isVisible():
                        any_velvoite_active = True
                        break
            
            # Luo nykyinen tila-dictionary
            current_state = {
                'active_ids': tuple(sorted(active_ids)),
                'any_velvoite_active': any_velvoite_active
            }
            
            # Vertaa edelliseen tilaan - päivitä vain jos muuttunut
            if last_state == current_state:
                return  # Ei muutoksia, ei tehdä mitään
            
            last_state = current_state
            
            # Tallenna project variableen
            QgsExpressionContextUtils.setProjectVariable(
                QgsProject.instance(),
                'active_kohdetyypit',
                ','.join(active_ids) if active_ids else 'none'
            )
            
            # Päivitä velvoitelayerit
            for layer_name, id_range in velvoite_layers.items():
                layers = QgsProject.instance().mapLayersByName(layer_name)
                if not layers:
                    continue
                
                layer = layers[0]
                
                # Velvoiteyhteenvedot käsitellään erikseen (ei velvoitemalli_id rajausta)
                if layer_name == 'Velvoiteyhteenvedot':
                    if active_ids:
                        yhteenveto_filter = f'"kohdetyyppi_id" IN ({",".join(active_ids)})'
                    else:
                        yhteenveto_filter = ''
                    
                    current_filter = layer.subsetString()
                    if current_filter != yhteenveto_filter:
                        layer.setSubsetString(yhteenveto_filter)
                        layer.triggerRepaint()
                    continue
                
                # Muut velvoitelayerit
                
                # Rakenna filter
                base_filter = f'"velvoitemalli_id" IN {id_range}'
                
                if active_ids:
                    kohde_filter = f'"kohdetyyppi_id" IN ({",".join(active_ids)})'
                    full_filter = f'{base_filter} AND {kohde_filter}'
                else:
                    full_filter = base_filter
                
                # Aseta filter vain jos se on muuttunut
                current_filter = layer.subsetString()
                if current_filter != full_filter:
                    layer.setSubsetString(full_filter)
                    layer.triggerRepaint()
            
            # Tarkista kuljetuslayerien näkyvyys
            # Päivitä kompostori ja kuljetus layerit
            for layer_name, id_range in kuljetus_kompostori_layers.items():
                layers = QgsProject.instance().mapLayersByName(layer_name)
                if not layers:
                    continue
                
                layer = layers[0]
                
                if active_ids:
                    kuljetus_komposti_filter = f'"kohdetyyppi_id" IN ({",".join(active_ids)})'
                else:
                    kuljetus_komposti_filter = ''
                
                current_filter = layer.subsetString()
                if current_filter != kuljetus_komposti_filter:
                    layer.setSubsetString(kuljetus_komposti_filter)
                    layer.triggerRepaint()

            # Säädä Kohteet-layerin läpinäkyvyys vain jos muuttunut
            current_opacity = kohteet_layer.opacity()
            target_opacity = 0.15 if any_velvoite_active else 1.0
            
            if abs(current_opacity - target_opacity) > 0.01:  # Vain jos ero merkittävä
                kohteet_layer.setOpacity(target_opacity)
                kohteet_layer.triggerRepaint()
        
        except Exception as e:
            print(f"Virhe suodattimien päivityksessä: {e}")
    
    # Päivitä heti
    last_state = None
    update_filters()
    
    # Luo timer joka päivittää 1 sekunnin välein
    update_timer = QTimer()
    update_timer.timeout.connect(update_filters)
    update_timer.start(1000)  # 1000ms = 1 sekunti
    
    print("Velvoitesuodattimet aktivoitu - päivittyy automaattisesti")


def saveProject():
    """Ajetaan kun projekti tallennetaan"""
    pass


def closeProject():
    """Ajetaan kun projekti suljetaan"""
    global update_timer, last_state
    if update_timer:
        update_timer.stop()
        update_timer = None
    last_state = None