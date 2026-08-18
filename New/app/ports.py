PORTS = [
    ("INBOM", "Mumbai", "India", 18.875, 72.78), ("INMUN", "Mundra", "India", 22.70, 69.58),
    ("INKOC", "Kochi", "India", 9.94, 76.20), ("INMAA", "Chennai", "India", 13.10, 80.34),
    ("INTUT", "Tuticorin", "India", 8.74, 78.24), ("INVTZ", "Visakhapatnam", "India", 17.68, 83.31),
    ("INPRT", "Paradip", "India", 20.25, 86.75), ("INHAL", "Kolkata–Haldia", "India", 21.95, 88.14),
    ("INKRI", "Krishnapatnam", "India", 14.24, 80.20), ("INMNG", "Mangalore", "India", 12.86, 74.78),
    ("INPAV", "Pipavav", "India", 20.89, 71.50), ("INJNP", "Nhava Sheva", "India", 18.91, 72.94),
    ("LKCMB", "Colombo", "Sri Lanka", 6.91, 79.78), ("LKHBA", "Hambantota", "Sri Lanka", 6.10, 81.08),
    ("LKTCO", "Trincomalee", "Sri Lanka", 8.55, 81.25), ("MVMLÉ", "Malé", "Maldives", 4.16, 73.46),
    ("PKKHI", "Karachi", "Pakistan", 24.78, 66.93), ("PKBQM", "Port Qasim", "Pakistan", 24.77, 67.32),
    ("BDCGP", "Chattogram", "Bangladesh", 22.20, 91.80), ("BDMGL", "Mongla", "Bangladesh", 21.72, 89.46),
    ("SGSIN", "Singapore", "Singapore", 1.17, 103.78), ("MYPKG", "Port Klang", "Malaysia", 2.98, 101.32),
    ("MYPEN", "Penang", "Malaysia", 5.40, 100.18), ("MYTPP", "Tanjung Pelepas", "Malaysia", 1.30, 103.54),
    ("IDJKT", "Jakarta", "Indonesia", -5.92, 106.82), ("IDSUB", "Surabaya", "Indonesia", -7.18, 112.68),
    ("IDBLW", "Belawan", "Indonesia", 3.82, 98.73), ("THLCH", "Laem Chabang", "Thailand", 13.03, 100.84),
    ("THBKK", "Bangkok", "Thailand", 13.39, 100.60), ("VNCLI", "Cai Mep", "Vietnam", 10.48, 107.00),
    ("MMRGN", "Yangon", "Myanmar", 16.54, 96.26), ("PHMNL", "Manila", "Philippines", 14.52, 120.88),
    ("AEDXB", "Dubai", "UAE", 25.28, 55.24), ("AEJEA", "Jebel Ali", "UAE", 24.96, 54.93),
    ("AEFJR", "Fujairah", "UAE", 25.14, 56.38), ("OMSLL", "Salalah", "Oman", 16.94, 54.02),
    ("OMMCT", "Muscat", "Oman", 23.65, 58.62), ("QADOH", "Doha", "Qatar", 25.35, 51.62),
    ("BHKBS", "Khalifa Bin Salman", "Bahrain", 26.20, 50.68), ("KWSAA", "Shuwaikh", "Kuwait", 29.37, 47.91),
    ("SAJED", "Jeddah", "Saudi Arabia", 21.45, 39.10), ("SAKAC", "King Abdullah Port", "Saudi Arabia", 22.54, 38.98),
    ("DJJIB", "Djibouti", "Djibouti", 11.59, 43.11), ("KEMBA", "Mombasa", "Kenya", -4.10, 39.69),
    ("TZDAR", "Dar es Salaam", "Tanzania", -6.82, 39.33), ("ZADUR", "Durban", "South Africa", -29.88, 31.08),
    ("ZACPT", "Cape Town", "South Africa", -33.88, 18.36), ("MZMPM", "Maputo", "Mozambique", -26.02, 32.98),
    ("MZBEW", "Beira", "Mozambique", -19.83, 35.04), ("MUPLU", "Port Louis", "Mauritius", -20.14, 57.47),
    ("SCRSE", "Port Victoria", "Seychelles", -4.61, 55.49), ("MGTOA", "Toamasina", "Madagascar", -18.14, 49.42),
    ("REPDG", "Port Réunion", "Réunion", -20.92, 55.27), ("AUPER", "Fremantle", "Australia", -32.05, 115.70),
    ("AUDRW", "Darwin", "Australia", -12.46, 130.77), ("AUADL", "Adelaide", "Australia", -34.78, 138.45),
    ("AUMEL", "Melbourne", "Australia", -37.87, 144.87), ("AUBNE", "Brisbane", "Australia", -27.34, 153.20),
    ("AUSYD", "Sydney", "Australia", -33.87, 151.30), ("AUPHE", "Port Hedland", "Australia", -20.30, 118.62),
]

PORT_BY_CODE = {p[0]: {"code": p[0], "name": p[1], "country": p[2], "lat": p[3], "lng": p[4]} for p in PORTS}


def public_ports():
    return list(PORT_BY_CODE.values())
