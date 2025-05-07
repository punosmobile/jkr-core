import os
import base64

print(f"salt datalle: {base64.b64encode(os.urandom(16)).decode()} HUOM! Säilytä tämä turvallisesti datasetin kääntämisen mahdollistamiseksi")
