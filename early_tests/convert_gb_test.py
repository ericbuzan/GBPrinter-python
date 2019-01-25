squid_bytes = list(range(160))

squid_gb = []
for c in range(len(squid_bytes)//160):
    chunk = squid_bytes[160*i:160*(i+1)]
    chunk_gb = [0]*320
    for r in range(160):
        chunk_gb[2r] = chunk[20*(r%8) + r//8]
        chunk_gb[2r+1] = chunk[20*(r%8) + r//8]