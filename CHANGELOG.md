# Changelog

All notable changes to this project will be documented in this file.

## [0.6.0] - 2025-01-30

### Added

- Building Classification 2018 (Rakennusluokka_2018)
  - Classification codes and mappings
  - Building classes integration into reporting system
  - Property type filtering with explanatory notes
- Comprehensive debug functions
- Linux shell script equivalent of `startdev.ps1`
- `lukittu` field to kohde table to indicate if the kohde is locked

### Changed

- Enhanced property type handling:
  - Improved property formation logic and validation
  - Enhanced type definition algorithms
  - Enhanced address number matching
  - Improved basic fee registry data processing
- Upgraded code documentation for better maintainability
- Fixed PostgreSQL 16 compatibility issues with DevDB public schema privileges

### Documentation

- Updated README.md with new features and configurations
- Added comprehensive code documentation
- Improved debug message clarity

## [0.6.1] - 2025-02-13

### Added

- Rakennusluokka_2018 integration:
  - Added to rakennukset view with selite
  - Enhanced building classification support
- QGIS project improvements:
  - New separate layers for kohdetyypit
  - Migration system for QGIS projects
  - Documentation for QGIS project migrations
- Lopetusilmoitus handling enhancements
- Enhanced logging and debugging capabilities
- Null date option in velvoite reports
- Type checking mode (basic) for Python analysis

### Fixed

- Kohdetyyppi determination logic:
  - Improved rakennusluokka_2018 checks
  - Enhanced building type validation
- Query optimizations:
  - Added proper parentheses in kohde filtering
  - Improved velvoite ordering with DESC, id DESC
  - Enhanced date range handling
- Kompostitietojen processing and validation
- Building data processing improvements:
  - Enhanced DVV building data handling
  - Improved building cluster logic
  - Better ownership and resident matching

### Changed

- Enhanced documentation:
  - Added QGIS project migration guide
  - Updated README.md with new configurations
- Improved data validation in velvoite system
- Optimized building data processing:
  - Added PRT tracking
  - Enhanced logging for building processing
  - Improved transaction handling

## [0.6.2] - 2025-02-17

### Fixed

- Velvoite processing repaired:
  - Fixed velvoite processing
  - Fixed Kohteiden loppupvm handling

## [0.6.3] - 2025-03-25

### Added

- Kohdetyyppi updates:
  - Kohteet that have changes in their rakennukset will now recheck and update their kohdetyyppi_id

### Fixed

- Kompostori processing fixes:
  - Kompostorin kohteet will no longer fail depending on a SQLAlchemy coin flip
  - Fixed a rare crash where sheet header was treated as a number instead of text

### Changes

- Log and comment changes:
  - Added slightly more identifiable log statements to several sections of code for improved debugging
  - Updated some outdated comments to match current functionality
- Report changes:
  - Report will now filter kunta based on kiinteistotunnus instead of postinumero

## [0.6.4] - 2025-04-4


### Fixed

- Building clustering logic fix 
  - Compare whole cluster to each potential building as a whole instead of per building

## [0.6.5] - 2025-04-16

### Added

- Added scripts for checking database role assignments and resetting database

### Fixed

- Fixes to bat file password handling

## [0.6.6] - 2025-05-07

### Added

- Added script for taking subsets of data from given dataset
- Added script for encrypting and decrypting whole datasets

### Fixed

- Fixes to import_dvv.sql where one column is written in wrong format

## [0.6.7] - 2025-05-27

### Added

- File containing default pseudonymization fields

- Database
  - Several new columns
  - Kunta column to v__rakennukset view
  - Updated QGis project

### Fixed

- Tests
  - Fixed most automated tests to work with current code
  - Enabled usage of tests in Linux operating systems
- Pseudonymizer
  - Fix for file replacer

## [0.6.8] - 2025-05-30

### Added

- A check during kohde creation which can remove a rakennus from kohde
  - Checks for changes in residents and owners
  - Is there a new resident and have they lived there longer than the last poimintapvm
  - Is the mover the buildings owner
  - Removes rakennus from kohde depending on results
- Added poimintapvm to database

### Fixed

- Tests
  - Some additional fixes to tests
  - Increased the amount of test rows in test data

## [0.6.9] - 2025-06-13

### Added

- Added import_hapa command for easy hapa data import

### Changed

- Kohde alkupvm is now dynamic and will use either owner or resident starting date and default to poimintapvm if neither is available
- If Kohde would end due to a building leaving it, it will be marked as expired and removed after active contracts and shipments have been moved to a new Kohde 

## [0.6.10] - 2025-06-23

### Fixed

- Kohde geometry will now be updated to match when building geometry is updated

### Added

- Added table descriping the scope of automated tests within the codebase

### Changed

- Switched Kunta_out value source to building.kunta column instead of kiinteistotunnus or postal address


## [0.6.11] - 2025-06-25

### Fixed

- Old kohde data will now be handled correctly when multiple expiring kohde objects are clustered together


## [0.7.0] - 2025-07-2

### Fixed

- Fixed a situation where an osapuoli who is the last resident and owner moved out of a building but would still be considered as current owner, failing to end the Kohde


## [0.7.1] - 2025-09-03

### Fixed

- Fixed mistake in migration files where some changes were being overwritten by repeatable migrations

## [0.7.2] - 2025-09-24

### Fixed

- Fixed incorrect kompostori ilmoitus, lopetus ilmoitus and kuljetus matching behaviour
- Fixed mistake in check_and_update_old_other_building_kohde_kohdetyyppi function where it did not account for null loppupvm
- Fixed mistake in check_and_update_old_other_building_kohde_kohdetyyppi function where it only affected kohdetyyppi 8

### Added

- Added AKP jätetyyppi
- Added AKP based sekajäte velvoite and velvoitemalli

### Changed

- Failure of biojäte yhteenvetomalli now returns "biojäte puuttuu"
- Removed tyhjennysväli päätös from sekajätevelvoite
- Altered sekajäte velvoite calculations
- Some changes to Kohde velvoite listings

## [0.7.3] - 2025-09-29

### Fixed

- Fixed mistake in Kuljetustieto import that caused extra kohde assignments to buildings
