import serial
import time
import pandas as pd
import matplotlib.pyplot as plt

# --- Configuração ---
PORTA = input("Porta COM (Mestre): ")
SF = input("SF (7-12): ")
QTD = int(input("Qtd de Pings: "))
TIMEOUT = 4.0 # Tempo máx de espera pela resposta

try:
    ser = serial.Serial(PORTA, 9600, timeout=1)
except Exception as e:
    print(f"Erro ao abrir porta: {e}")
    exit()

# --- Configura SF Rapidamente ---
def configurar_sf(ser, sf):
    print(f"Configurando SF{sf}...")
    ser.write(b"+++")
    time.sleep(1.0)
    ser.read_all()
    cmd = f"AT+SF{sf}\r\n".encode()
    ser.write(cmd)
    time.sleep(0.5)
    ser.write(b"+++") # Sai do modo AT
    time.sleep(1.0)
    ser.read_all()
    print("Pronto para o teste de Ping-Pong!\n")

configurar_sf(ser, SF)

dados = []

print(f"{'='*40}")
print(f"INICIANDO PING-PONG ({QTD} pacotes)")
print(f"{'='*40}")

try:
    for i in range(1, QTD + 1):
        msg_envio = f"PING#{i}"
        
        # 1. Limpa sujeira antiga
        ser.reset_input_buffer()
        
        # 2. Envia e Marca Tempo Inicial (t0)
        t0 = time.perf_counter() # perf_counter é mais preciso que time.time()
        ser.write(f"{msg_envio}\r\n".encode('utf-8'))
        
        print(f"--> Enviado: {msg_envio}", end=" | ")
        
        # 3. Aguarda Resposta (Polling com Timeout manual)
        recebido = False
        msg_resposta = ""
        
        # Loop de espera "Busy Wait" para precisão
        while (time.perf_counter() - t0) < TIMEOUT:
            if ser.in_waiting:
                try:
                    linha = ser.readline().decode('utf-8', errors='ignore').strip()
                    # Verifica se é a resposta esperada (PONG do mesmo ID)
                    if f"PONG#{i}" in linha:
                        t1 = time.perf_counter() # Marca Tempo Final (t1)
                        recebido = True
                        msg_resposta = linha
                        break
                except:
                    pass
        
        # 4. Cálculos
        if recebido:
            rtt = t1 - t0
            metade_rtt = rtt / 2
            print(f"<-- Recebido: {msg_resposta} | RTT: {rtt:.4f}s | ToA Est.: {metade_rtt:.4f}s")
            
            dados.append({
                "ID": i,
                "Status": "Sucesso",
                "RTT_s": rtt,
                "ToA_Estimado_s": metade_rtt
            })
        else:
            print("x Perda (Timeout)")
            dados.append({
                "ID": i,
                "Status": "Perdido",
                "RTT_s": None,
                "ToA_Estimado_s": None
            })
            
        time.sleep(1.0) # Intervalo entre pings

except KeyboardInterrupt:
    print("\nTeste interrompido.")

finally:
    ser.close()

    # --- Relatório Rápido ---
    if dados:
        df = pd.DataFrame(dados)
        sucessos = df[df["Status"] == "Sucesso"]
        
        if not sucessos.empty:
            media_toa = sucessos["ToA_Estimado_s"].mean()
            print("\n" + "="*40)
            print(f"RESULTADO FINAL (SF{SF})")
            print(f"Pacotes Enviados: {len(df)}")
            print(f"Pacotes Recebidos: {len(sucessos)}")
            print(f"Perda: {len(df) - len(sucessos)}")
            print(f"Média Time on Air (Estimado): {media_toa:.4f} s")
            print("="*40)
            
            # Gráfico Simples
            plt.figure(figsize=(10,5))
            plt.plot(sucessos['ID'], sucessos['ToA_Estimado_s'], marker='o')
            plt.axhline(y=media_toa, color='r', linestyle='--', label='Média')
            plt.title(f"Time on Air Estimado (RTT / 2) - SF{SF}")
            plt.ylabel("Segundos")
            plt.xlabel("ID do Pacote")
            plt.legend()
            plt.grid()
            plt.show()
        else:
            print("Nenhum pacote retornou.")
