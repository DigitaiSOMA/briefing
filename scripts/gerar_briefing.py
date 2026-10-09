#!/usr/bin/env python3
"""Gera <slug>/index.html a partir de <slug>/questionario.json.

O mesmo JSON alimenta o questionário do portal (tabela `questionarios.secoes`),
então web e app mostram as mesmas perguntas. O visual, o cabeçalho e o envio
continuam os da página existente: só o formulário e os rótulos do resumo são trocados.

Uso: python3 scripts/gerar_briefing.py feliz-nu-simples
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
slug = sys.argv[1]
page = ROOT / slug / "index.html"
q = json.loads((ROOT / slug / "questionario.json").read_text())
src = page.read_text()
e = lambda s: html.escape(s or "", quote=True)


def opt_val(o):
    return o if isinstance(o, str) else o["valor"]


def pergunta(p):
    req = p.get("obrigatoria")
    star = ' <span class="req">*</span>' if req else ""
    ajuda = f'<p class="h">{e(p["ajuda"])}</p>' if p.get("ajuda") else ""
    t, pid = p["tipo"], p["id"]
    if t in ("texto", "texto_longo"):
        tag = "textarea" if t == "texto_longo" else "input"
        attrs = f'id="{pid}" name="{pid}" placeholder="{e(p.get("placeholder"))}"' + (" required" if req else "")
        field = f"<textarea {attrs}></textarea>" if tag == "textarea" else f'<input type="text" {attrs}>'
        return f'  <div class="q"><label class="t" for="{pid}">{e(p["titulo"])}{star}</label>{ajuda}\n    {field}\n  </div>'
    if t == "imagem_escolha":
        btns = []
        for o in p["opcoes"]:
            v = opt_val(o)
            img = o.get("imagem") if isinstance(o, dict) else None
            if img:
                rel = img.split(f"/{slug}/", 1)[-1]
                btns.append(f'<button type="button" class="opt" data-value="{e(v)}"><img alt="" src="{e(rel)}" loading="lazy"><span>{e(v)}</span></button>')
            else:
                btns.append(f'<button type="button" class="opt noimg" data-value="{e(v)}"><span>{e(v)}</span></button>')
        data = f'data-name="{pid}"' + (' data-required="1"' if req else "")
        return f'  <div class="q"><label class="t">{e(p["titulo"])}{star}</label>{ajuda}\n    <div class="opts" {data}>\n      ' + "\n      ".join(btns) + "\n    </div>\n  </div>"
    opcoes = ["Sim", "Não"] if t == "sim_nao" else [opt_val(o) for o in p["opcoes"]]
    data = f'data-name="{pid}"'
    if t == "multipla":
        data += ' data-multi="1"'
        if p.get("max"):
            data += f' data-max="{p["max"]}"'
    if req:
        data += ' data-required="1"'
    chips = "".join(f'<button type="button" class="chip">{e(o)}</button>' for o in opcoes)
    return f'  <div class="q"><label class="t">{e(p["titulo"])}{star}</label>{ajuda}\n    <div class="chips" {data}>{chips}</div>\n  </div>'


def titulo_html(t):
    # primeira palavra normal, resto destacado (padrão visual da página)
    w = t.split(" ", 1)
    return e(w[0]) + (f" <em>{e(w[1])}</em>" if len(w) > 1 else "")


secoes = q["secoes"]
n = len(secoes)
out = []
for i, s in enumerate(secoes):
    lead = f'\n  <p class="lead">{e(s["descricao"])}</p>' if s.get("descricao") else ""
    body = "\n".join(pergunta(p) for p in s["perguntas"])
    extra = '\n  <button type="button" class="btn send" id="send">Enviar respostas</button>\n  <p class="msg" id="sendmsg"></p>' if i == n - 1 else ""
    out.append(f'<section class="step{" on" if i == 0 else ""}" data-step="{i}">\n  <p class="eyebrow">Passo {i + 1} de {n}</p>\n  <h1>{titulo_html(s["titulo"])}</h1>{lead}\n{body}{extra}\n</section>')
form = '<form id="f" novalidate>\n\n' + "\n\n".join(out) + "\n\n</form>"
src, k = re.subn(r'<form id="f" novalidate>.*?</form>', lambda m: form, src, flags=re.S)
assert k == 1

labels = {p["id"]: p["titulo"] for s in secoes for p in s["perguntas"]}
src, k = re.subn(r"var labels=\{.*?\};", lambda m: "var labels=" + json.dumps(labels, ensure_ascii=False) + ";", src, flags=re.S)
assert k == 1
src = re.sub(r'<span class="counter" id="counter">\d+ / \d+</span>', f'<span class="counter" id="counter">1 / {n}</span>', src)
src = src.replace("msg.textContent='Falta preencher: nome.'", "msg.textContent='Falta preencher um campo obrigatório (*).'")

# rascunho: chave v2, aproveitando o que já foi digitado na v1
src = re.sub(r'var KEY = "([a-z0-9-]+)-v\d+";', r'var KEY = "\1-v2";', src)
if "KEY_V1" not in src:
    src = src.replace(
        "try { state = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch(e){ state = {}; }",
        "try { state = JSON.parse(localStorage.getItem(KEY) || localStorage.getItem(KEY.replace(/-v2$/,'-v1')) || '{}') || {}; } catch(e){ state = {}; } /* KEY_V1 */",
    )
# envio de teste identificado: ?teste=1 marca a linha
if "TESTE-" not in src:
    src = src.replace("var payload={ cliente: CFG.cliente, projeto: CFG.projeto,",
                      "var teste=/[?&]teste=1/.test(location.search);\n    var payload={ cliente: CFG.cliente, projeto: (teste?'TESTE-':'')+CFG.projeto,")
if ".opt.noimg" not in src:
    src = src.replace("</style>", ".opt.noimg{display:flex;align-items:center;justify-content:center;min-height:96px}\n</style>", 1)

page.write_text(src)
print(f"{page}: {n} etapas, {len(labels)} perguntas")
