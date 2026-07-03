import subprocess, os, signal, time

# Find processes holding port 8000
result = subprocess.run('netstat -ano', capture_output=True, text=True, shell=True)
pids = []
for line in result.stdout.split('\n'):
    if 'LISTENING' in line and ':8000' in line:
        parts = [p for p in line.strip().split() if p]
        if parts:
            pid = parts[-1]
            pids.append(pid)
            print(f'Found PID {pid}')
            subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
            print(f'taskkill sent to {pid}')

time.sleep(3)

s = __import__('socket').socket()
if s.connect_ex(('127.0.0.1', 8000)) == 0:
    print('Port STILL in use')
else:
    print('Port is FREE')
s.close()
