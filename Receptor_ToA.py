import serial
import time
import re

PORTA = input("Porta COM (Escravo/Echo): ")
SF = input("SF (7-12): ")

try:
    ser = serial.Serial(PORTA, 9600, timeout=1)
except Exception as e:
    print(f"Erro: {e}")
    exit()

def configurar_sf(ser, sf):
    print(f"Configurando SF{sf}...")
    ser.write(b"+++")
    time.sleep(1.0)
    ser.read_all()
    ser.write(f"AT+SF{sf}\r\n".encode())
    time.sleep(0.5)
    ser.write(b"+++")
    time.sleep(1.0)
    ser.reset_input_buffer()
    print("Modo Escravo (Echo) Ativo. Aguardando Pings...\n")

configurar_sf(ser, SF)

try:
    while True:
        if ser.in_waiting:
            try:
                # Leitura
                raw = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Se for um PING válido
                if "PING#" in raw:
                    # 1. Extrai o ID
                    match = re.search(r'PING#(\d+)', raw)
                    if match:
                        pkt_id = match.group(1)
                        
                        # 2. RESPOSTA IMEDIATA (Prioridade Máxima)
                        # Não fazemos prints nem checagem de RSSI antes disso
                        resp = f"PONG#{pkt_id}\r\n"
                        ser.write(resp.encode('utf-8'))
                        
                        # 3. Agora sim, logamos na tela (fora do tempo crítico)
                        print(f"[RX] {raw} -> [TX] {resp.strip()}")
                        
            except Exception as e:
                print(f"Erro loop: {e}")

except KeyboardInterrupt:
    print("\nEncerrado.")
finally:
    ser.close()