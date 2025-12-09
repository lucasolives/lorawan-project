import serial
import time
import re
import pandas as pd
import matplotlib.pyplot as plt

# --- Funções de Hardware (Smart Toggle & RSSI) ---
def limpar_buffer(ser):
    ser.reset_input_buffer()
    ser.reset_output_buffer()

def enviar_bytes(ser, texto):
    cmd = f"{texto}\r\n".encode('utf-8')
    ser.write(cmd)

def garantir_entrada_modo_at(ser):
    for _ in range(2):
        limpar_buffer(ser)
        enviar_bytes(ser, "+++")
        time.sleep(1.0)
        resp = ser.read_all().decode('utf-8', errors='ignore').lower()
        if "entry at" in resp: return True
        if "exit at" in resp: 
            time.sleep(0.5)
            continue
    return False

def extrair_rssi(texto):
    # Tenta achar número negativo (ex: -105)
    match = re.search(r'(-\d{2,3})', texto)
    if match: return int(match.group(1))
    return None

def obter_rssi_inteligente(ser):
    if not garantir_entrada_modo_at(ser): return None
    
    limpar_buffer(ser)
    enviar_bytes(ser, "AT+RSSI")
    time.sleep(0.5)
    raw = ser.read_all().decode('utf-8', errors='ignore')
    
    enviar_bytes(ser, "+++")
    time.sleep(0.5)
    ser.read_all() # Limpa saída
    
    return extrair_rssi(raw)

def configurar_sf(ser, sf):
    print(f"--- Configurando SF para {sf} ---")
    garantir_entrada_modo_at(ser)
    enviar_bytes(ser, f"AT+SF{sf}")
    time.sleep(0.5)
    print(f"Resp SF: {ser.read_all().decode('utf-8', errors='ignore').strip()}")
    enviar_bytes(ser, "+++")
    time.sleep(1.0)
    ser.reset_input_buffer()
    print("Pronto para receber!\n")

# --- Análise de Dados ---
def extrair_id_pacote(msg):
    # Procura por "#123" na mensagem
    match = re.search(r'#(\d+)', msg)
    if match: return int(match.group(1))
    return None

def gerar_relatorio(dados, total_esperado):
    if not dados:
        print("Nenhum dado recebido para gerar relatório.")
        return

    df = pd.DataFrame(dados)
    
    # 1. Tabela de Recebimento
    print("\n" + "="*40)
    print("TABELA DE DADOS RECEBIDOS")
    print("="*40)
    print(df.to_string(index=False))
    
    # 2. Estatísticas
    recebidos = len(df)
    perda = total_esperado - recebidos
    perda_pct = (perda / total_esperado) * 100 if total_esperado > 0 else 0
    rssi_medio = df['RSSI'].mean()
    
    print("\n" + "="*40)
    print("ESTATÍSTICAS FINAIS")
    print(f"Pacotes Esperados: {total_esperado}")
    print(f"Pacotes Recebidos: {recebidos}")
    print(f"Pacotes Perdidos:  {perda}")
    print(f"Packet Loss Rate:  {perda_pct:.2f}%")
    print(f"RSSI Médio:        {rssi_medio:.2f} dBm")
    print("="*40)

    # 3. Gráficos
    plt.figure(figsize=(10, 6))
    
    # Gráfico de RSSI por ID do Pacote
    plt.plot(df['ID'], df['RSSI'], marker='o', linestyle='-', color='b', label='RSSI (dBm)')
    
    # Linha de média
    plt.axhline(y=rssi_medio, color='r', linestyle='--', label=f'Média ({rssi_medio:.1f})')
    
    plt.title(f'Performance LoRa (SF selecionado) - Perda: {perda_pct:.1f}%')
    plt.xlabel('ID do Pacote (Sequência)')
    plt.ylabel('RSSI (dBm)')
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    plt.legend()
    
    # Ajusta limites para ficar bonito
    plt.ylim(df['RSSI'].min() - 5, df['RSSI'].max() + 5)
    
    print("Exibindo gráfico...")
    plt.show()

# --- Main ---
def main():
    print("### Receptor LoRa Analytics ###")
    porta = input("Porta COM: ")
    sf = input("SF (7-12): ")
    total_esperado = int(input("Quantos pacotes você pretende enviar? (Para cálculo de perda): "))
    
    try:
        ser = serial.Serial(porta, 9600, timeout=1)
    except Exception as e:
        print(f"Erro: {e}")
        return

    configurar_sf(ser, sf)
    limpar_buffer(ser)

    dados_coletados = []
    
    print(f"Aguardando {total_esperado} pacotes... (Ctrl+C para encerrar forçadamente)")

    try:
        while len(dados_coletados) < total_esperado:
            if ser.in_waiting > 0:
                raw_msg = ser.readline().decode('utf-8', errors='ignore').strip()
                if not raw_msg or raw_msg in ["OK", "ERROR"] or "AT" in raw_msg: continue

                print(f"[RX] Msg: {raw_msg}", end=" | ")
                
                # 1. Ler RSSI
                rssi = obter_rssi_inteligente(ser)
                print(f"RSSI: {rssi} dBm")
                
                # 2. Processar Dados
                pkt_id = extrair_id_pacote(raw_msg)
                
                # Se não conseguiu extrair ID, usa um contador sequencial provisório ou 0
                if pkt_id is None:
                    pkt_id = len(dados_coletados) + 1
                
                # Salva apenas se RSSI for válido para não quebrar o gráfico
                if rssi is not None:
                    dados_coletados.append({
                        "ID": pkt_id,
                        "Mensagem": raw_msg,
                        "RSSI": rssi
                    })
                
                limpar_buffer(ser)

    except KeyboardInterrupt:
        print("\n\nColeta interrompida pelo usuário.")
    
    finally:
        ser.close()
        # Gera relatório mesmo se parou antes ou se acabou
        gerar_relatorio(dados_coletados, total_esperado)

if __name__ == "__main__":
    main()