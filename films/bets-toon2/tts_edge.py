"""Microsoft Edge TTS (grátis) com o certificado do proxy desta máquina. Uso: tts_edge.py lines.json out_dir"""
import asyncio, json, os, ssl, sys
import edge_tts, edge_tts.communicate as C
CA = os.environ.get('EDGE_CA', '/root/.ccr/ca-bundle.crt')
if os.path.exists(CA): C._SSL_CTX = ssl.create_default_context(cafile=CA)
async def one(L, out):
    p = os.path.join(out, L['id'] + '.mp3')
    if os.path.exists(p) and os.path.getsize(p) > 0 and not L.get('force'): return
    c = edge_tts.Communicate(L.get('say', L['text']), L.get('voice', 'pt-BR-AntonioNeural'), rate=L.get('rate', '+10%'), pitch=L.get('pitch', '+0Hz'))
    await c.save(p)
async def main():
    lines = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    for L in lines: await one(L, out); print('ok', L['id'])
asyncio.run(main())
