import serial
import time

# --- Funções Auxiliares (Smart Toggle) ---
def limpar_buffer(ser):
    ser.reset_input_buffer()
    ser.reset_output_buffer()

def enviar_bytes(ser, texto):
    cmd = f"{texto}\r\n".encode('utf-8')
    ser.write(cmd)

def garantir_entrada_modo_at(ser):
    max_tentativas = 2
    for tentativa in range(max_tentativas):
        limpar_buffer(ser)
        enviar_bytes(ser, "+++")
        time.sleep(1.0)
        resposta = ser.read_all().decode('utf-8', errors='ignore').lower()
        
        if "entry at" in resposta:
            return True
        elif "exit at" in resposta:
            time.sleep(0.5)
            continue
    return False

def configurar_sf(ser, sf):
    print(f"--- Configurando SF para {sf} ---")
    if not garantir_entrada_modo_at(ser):
        print("[ERRO] Falha ao entrar no modo AT. SF pode estar incorreto.")
        return

    enviar_bytes(ser, f"AT+SF{sf}")
    time.sleep(0.5)
    resp = ser.read_all().decode('utf-8', errors='ignore').strip()
    print(f"Resposta SF: {resp}")
    
    enviar_bytes(ser, "+++")
    time.sleep(1.0)
    ser.reset_input_buffer()
    print("Módulo pronto para transmitir!\n")

# --- Main ---
def main():
    print("### Transmissor LoRa - Gerador de Dados ###")
    porta = input("Digite a porta COM: ")
    sf = input("SF (7-12): ")
    
    try:
        ser = serial.Serial(porta, 9600, timeout=1)
    except Exception as e:
        print(f"Erro: {e}")
        return

    configurar_sf(ser, sf)

    print("-" * 30)
    qtd = int(input("Quantidade de pacotes a enviar: "))
    intervalo = float(input("Intervalo entre envios (segundos): "))
    msg_base = "Pkt" # Prefixo curto
    print("-" * 30)

    try:
        for i in range(1, qtd + 1):
            # Formato: "Pkt #1", "Pkt #2"
            msg_final = f"{msg_base} #{i}"
            enviar_bytes(ser, msg_final)
            print(f"[{i}/{qtd}] Enviado: {msg_final}")
            
            if i < qtd:
                time.sleep(intervalo)
        
        print("\nEnvio concluído.")
    except KeyboardInterrupt:
        print("\nCancelado.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()