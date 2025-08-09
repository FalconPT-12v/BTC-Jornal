#!/usr/bin/env python3
import requests
import binascii
import time
import sys
import sqlite3

API_BASE = "https://blockstream.info/api"
INITIAL_BLOCKS = 30
DB_FILE = "btc_jornal.db"

MESSAGES = {
    'pt': {
        'choose_lang': "Escolha idioma / Choose language: [pt/en] ",
        'intro': (
            "📡 BTC Jornal CLI iniciado\n\n"
            "Este programa busca mensagens OP_RETURN na blockchain Bitcoin\n"
            "que começam com '/BJ' e as destaca como mensagens do BTC Jornal Mundial.\n"
            "As mensagens podem conter qualquer conteúdo, incluindo links.\n"
            "⚠️ Atenção: cuidado com links maliciosos e conteúdos não verificados.\n"
            "Use com responsabilidade.\n\n"
            "Pressione Enter para avançar para o próximo bloco, ou 'q' para sair.\n"
        ),
        'block': "📦 Bloco {height} ({hash})\n",
        'saving_msg': "💾 Salvando mensagem /BJ no banco de dados.",
        'exit': "\n👋 Encerrando BTC Jornal CLI.",
        'support': "💡 Motive o desenvolvedor / Support the developer",
        'btc_addr': "   BTC: bc1qfvh7lwy7rrazsxdmdtjpx70ytjg3shgh6rtlm0",
        'error': "⚠️ Erro: {error}",
        'prompt_next': "Pressione Enter para próximo bloco, ou 'q' para sair: ",
    },
    'en': {
        'choose_lang': "Escolha idioma / Choose language: [pt/en] ",
        'intro': (
            "📡 BTC Jornal CLI started\n\n"
            "This program fetches OP_RETURN messages from the Bitcoin blockchain\n"
            "that start with '/BJ' and highlights them as BTC World Journal messages.\n"
            "Messages may contain any content, including links.\n"
            "⚠️ Warning: be careful with malicious links and unverified content.\n"
            "Use responsibly.\n\n"
            "Press Enter to move to the next block, or 'q' to quit.\n"
        ),
        'block': "📦 Block {height} ({hash})\n",
        'saving_msg': "💾 Saving /BJ message to database.",
        'exit': "\n👋 Exiting BTC Jornal CLI.",
        'support': "💡 Support the developer",
        'btc_addr': "   BTC: bc1qfvh7lwy7rrazsxdmdtjpx70ytjg3shgh6rtlm0",
        'error': "⚠️ Error: {error}",
        'prompt_next': "Press Enter for next block, or 'q' to quit: ",
    }
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS jornal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bloco INTEGER,
            txid TEXT,
            mensagem TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(bloco, txid, mensagem):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO jornal (bloco, txid, mensagem) VALUES (?, ?, ?)",
              (bloco, txid, mensagem))
    conn.commit()
    conn.close()

def get_latest_block_height():
    return int(requests.get(f"{API_BASE}/blocks/tip/height").text)

def get_block_hash(height):
    return requests.get(f"{API_BASE}/block-height/{height}").text

def get_block_txs(block_hash):
    return requests.get(f"{API_BASE}/block/{block_hash}/txs").json()

def extract_opreturn_messages(tx):
    msgs = []
    for vout in tx['vout']:
        script = vout['scriptpubkey']
        if script.startswith("6a"):  # OP_RETURN
            try:
                hex_data = script[4:]
                text = binascii.unhexlify(hex_data).decode('utf-8', errors='ignore')
                msgs.append(text)
            except:
                pass
    return msgs

def destaque_bj(msg, lang):
    YELLOW_BG = '\033[43m'
    BLACK_BOLD = '\033[1;30m'
    RESET = '\033[0m'

    if lang == 'pt':
        destaque_texto = "/BJ BTC Jornal Mundial"
    else:
        destaque_texto = "/BJ BTC World Journal"

    linhas = [destaque_texto] + [''] + msg.strip().split('\n')
    largura = max(len(l) for l in linhas)
    borda = '*' * (largura + 6)

    print(f"\n{YELLOW_BG}{BLACK_BOLD}{borda}{RESET}")
    for linha in linhas:
        print(f"{YELLOW_BG}{BLACK_BOLD}** {linha.ljust(largura)} **{RESET}")
    print(f"{YELLOW_BG}{BLACK_BOLD}{borda}{RESET}\n")

def process_block(height, lang):
    block_hash = get_block_hash(height)
    txs = get_block_txs(block_hash)
    print(MESSAGES[lang]['block'].format(height=height, hash=block_hash))

    for tx in txs:
        msgs = extract_opreturn_messages(tx)
        for msg in msgs:
            if msg.startswith("/BJ"):
                destaque_bj(msg, lang)
                save_message(height, tx['txid'], msg)
            else:
                print(f"📝 {msg}")

def main():
    lang = ''
    while lang not in ['pt', 'en']:
        lang = input(MESSAGES['en']['choose_lang']).strip().lower()

    print(MESSAGES[lang]['intro'])

    init_db()

    latest_block = get_latest_block_height()
    start_block = max(0, latest_block - INITIAL_BLOCKS + 1)

    # Mostrar os últimos blocos, aguardando controle do usuário
    for height in range(start_block, latest_block + 1):
        process_block(height, lang)
        resp = input(MESSAGES[lang]['prompt_next']).strip().lower()
        if resp == 'q':
            print(MESSAGES[lang]['exit'])
            print(MESSAGES[lang]['support'])
            print(MESSAGES[lang]['btc_addr'])
            sys.exit()

    # Monitorar novos blocos na mesma lógica
    last_checked_block = latest_block
    while True:
        try:
            current_block = get_latest_block_height()
            if current_block > last_checked_block:
                for height in range(last_checked_block + 1, current_block + 1):
                    process_block(height, lang)
                    resp = input(MESSAGES[lang]['prompt_next']).strip().lower()
                    if resp == 'q':
                        print(MESSAGES[lang]['exit'])
                        print(MESSAGES[lang]['support'])
                        print(MESSAGES[lang]['btc_addr'])
                        sys.exit()
                last_checked_block = current_block
            else:
                time.sleep(10)
        except KeyboardInterrupt:
            print(MESSAGES[lang]['exit'])
            print(MESSAGES[lang]['support'])
            print(MESSAGES[lang]['btc_addr'])
            sys.exit()
        except Exception as e:
            print(MESSAGES[lang]['error'].format(error=str(e)))
            time.sleep(5)

if __name__ == "__main__":
    main()
