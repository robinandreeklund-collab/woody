"""Master/slave-nätverk för woody.

Varje Jetson (läshuvud + sensorer) kör en **slave** (``app.net.slave``) som
exponerar sin ``DeviceManager`` + kalibrering över TCP (JSON-lines, Qt Network).
Din desktop kör **master**-GUI:t (``python -m app --master``) som ansluter till
alla noder ur ``data/nodes.json`` och styr dem var för sig.

Lagren:
  * ``protocol``        — JSON-lines-inramning + kommando-/event-namn (rent, testbart).
  * ``command_handler`` — översätter kommandon → DeviceManager-anrop (testbart).
  * ``slave_server``    — QTcpServer-transport på Jetsonen.
  * ``remote_node``     — klient som SPEGLAR DeviceManager-gränssnittet (QML-kompatibelt).
  * ``node_manager``    — laddar nodlistan, håller en RemoteNode per Jetson.
"""
