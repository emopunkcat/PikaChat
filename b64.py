import base64
import json
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    clear_screen()
    print("╔════════════════════════════╗")
    print("║       Config Manager       ║")
    print("║                            ║")
    print("╚════════════════════════════╝")
    print()

def encode_config():
    print("\n[ ENCODING MODE ]")
    while True:
        input_file = input("Enter path to config.json: ").strip()
        if os.path.exists(input_file):
            break
        print("File not found! (╯°□°）╯︵ ┻━┻")

    with open(input_file, 'r') as f:
        config_data = json.load(f)
    
    base64_str = base64.b64encode(json.dumps(config_data).encode('utf-8')).decode('utf-8')
    
    print("\n⚡ Encoding successful! Here's your Base64:")
    print("-"*40)
    print(base64_str)
    print("-"*40)

    output_file = ("export.conf").strip()
    with open(output_file, 'w') as f:
        f.write(base64_str)
    print(f"Saved to {output_file}! ⚡")    

def decode_config():
    print("\n[ DECODING MODE ]")
    base64_input = input("Enter Base64 string or export.conf path: ").strip()
    
    if os.path.exists(base64_input):
        with open(base64_input, 'r') as f:
            base64_str = f.read()
    else:
        base64_str = base64_input
    
    try:
        json_str = base64.b64decode(base64_str.encode('utf-8')).decode('utf-8')
        config_data = json.loads(json_str)
        
        print("\n⚡ Decoding successful! Here's a preview:")
        print("-"*40)
        print(json.dumps(config_data, indent=4)[:500] + ("..." if len(json_str) > 500 else ""))
        print("-"*40)
        
        output_file = input("\nEnter output filename (e.g. config.json): ").strip()
        with open(output_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Config saved to {output_file}! (★ω★)b")
        
    except Exception as e:
        print(f"Invalid Base64! {e} (╥﹏╥)")

def main_menu():
    show_banner()
    print("1. Encode JSON to Base64")
    print("2. Decode Base64 to JSON")
    print("3. Exit")
    choice = input("\nChoose an option (1-3): ").strip()
    
    if choice == '1':
        encode_config()
    elif choice == '2':
        decode_config()
    elif choice == '3':
        print("\nGoodbye! ⚡ ﾉʕ•ᴥ•ʔﾉ")
        exit()
    else:
        print("Invalid choice! ヽ(`Д´)ﾉ")
    
    input("\nPress Enter to continue...")
    main_menu()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nPika pika! (×_×)⌒☆")
        exit()