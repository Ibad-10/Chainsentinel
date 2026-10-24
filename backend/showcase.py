REAL = [
 dict(chain="eth", address="0x098B716B8Aaf21512996dC57EB0615e2383E2f96", title="Ronin Bridge Exploiter (Lazarus, OFAC)", expected="violation"),
 dict(chain="eth", address="0x0d043128146654C7683Fbf30ac98D7B2285DeD00", title="Harmony Bridge Exploiter (Lazarus)", expected="violation"),
 dict(chain="eth", address="0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2", title="Bybit Exploiter (Lazarus, Feb 2025)", expected="violation"),
 dict(chain="eth", address="0x28C6c06298d514Db089934071355E5743bf21d60", title="Binance 14 hot wallet (look-alike)", expected="supported"),
 dict(chain="eth", address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", title="vitalik.eth (public figure; used Tornado Cash in 2020)", expected="violation"),
 dict(chain="eth", address="0x8caa5e923374116A4024139bd8382f16A715402c", title="Ordinary sweeper wallet (random, deposit forwarding)", expected="supported"),
 dict(chain="btc", address="12QtD5BFwRsdNsAZY76UVE1xyCGNTojH9h", title="OFAC-listed BTC address", expected="violation"),
 dict(chain="btc", address="15Zt2mKuQ5Qy6DEXfDcbtsEVneoGQQXrS4", title="OFAC-listed BTC address #2", expected="violation"),
]
