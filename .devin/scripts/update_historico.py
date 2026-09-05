#!/usr/bin/env python3
"""
Hook script para automaticamente documentar discussões, decisões e implementações
no arquivo HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Caminho do arquivo de histórico
HISTORICO_PATH = "docs/HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md"
# Arquivo temporário para armazenar dados da sessão
SESSION_DATA_PATH = ".devin/session_data.json"

def read_session_data():
    """Lê os dados acumulados da sessão atual"""
    if os.path.exists(SESSION_DATA_PATH):
        with open(SESSION_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"prompts": [], "tools_used": []}

def write_session_data(data):
    """Escreve os dados da sessão atual"""
    os.makedirs(".devin", exist_ok=True)
    with open(SESSION_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def handle_user_prompt(data):
    """Captura o prompt do usuário"""
    session_data = read_session_data()
    prompt = data.get("prompt", "")
    # Garante encoding correto
    if isinstance(prompt, str):
        prompt = prompt.encode('utf-8', errors='ignore').decode('utf-8')
    if prompt:
        session_data["prompts"].append({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt
        })
    write_session_data(session_data)
    return None

def handle_post_tool_use(data):
    """Captura informações sobre ferramentas usadas"""
    session_data = read_session_data()
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    
    # Filtra apenas ferramentas relevantes para documentação
    relevant_tools = ["edit", "write", "exec", "read"]
    if tool_name in relevant_tools:
        session_data["tools_used"].append({
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "input": tool_input,
            "success": tool_response.get("success", False)
        })
    write_session_data(session_data)
    return None

def handle_session_end(data):
    """Processa o fim da sessão e atualiza o histórico"""
    session_data = read_session_data()
    
    if not session_data["prompts"] and not session_data["tools_used"]:
        # Sessão vazia, não adiciona nada
        if os.path.exists(SESSION_DATA_PATH):
            os.remove(SESSION_DATA_PATH)
        return None
    
    # Gera entrada para o histórico
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    section_number = get_next_section_number()
    
    entry = f"""
## {section_number}. Sessão de {timestamp}

**Prompts do usuário:**

"""
    
    for i, prompt_data in enumerate(session_data["prompts"], 1):
        entry += f"{i}. {prompt_data['prompt']}\n"
    
    if session_data["tools_used"]:
        entry += "\n**Ferramentas utilizadas:**\n\n"
        
        # Agrupa por tipo de ferramenta
        tools_by_type = {}
        for tool_data in session_data["tools_used"]:
            tool_name = tool_data["tool"]
            if tool_name not in tools_by_type:
                tools_by_type[tool_name] = []
            tools_by_type[tool_name].append(tool_data)
        
        for tool_name, tools in tools_by_type.items():
            entry += f"- {tool_name}: {len(tools)} vez(es)\n"
    
    entry += "\n---\n"
    
    # Adiciona ao arquivo de histórico
    add_to_historico(entry)
    
    # Limpa dados da sessão
    if os.path.exists(SESSION_DATA_PATH):
        os.remove(SESSION_DATA_PATH)
    
    return None

def get_next_section_number():
    """Determina o próximo número de seção"""
    if not os.path.exists(HISTORICO_PATH):
        return 1
    
    with open(HISTORICO_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Procura por seções existentes
    import re
    sections = re.findall(r'^## (\d+)\.', content, re.MULTILINE)
    if sections:
        return max(int(s) for s in sections) + 1
    return 1

def add_to_historico(entry):
    """Adiciona uma entrada ao arquivo de histórico"""
    # Se o arquivo não existe, cria com cabeçalho
    if not os.path.exists(HISTORICO_PATH):
        os.makedirs("docs", exist_ok=True)
        with open(HISTORICO_PATH, 'w', encoding='utf-8') as f:
            f.write("# Histórico de evolução do TCC e do EdgeSimPy\n\n")
            f.write("Este documento registra automaticamente as sessões de trabalho.\n\n")
    
    # Adiciona a nova entrada
    with open(HISTORICO_PATH, 'a', encoding='utf-8') as f:
        f.write(entry)

def main():
    """Função principal"""
    # Configura encoding para Windows
    if sys.platform == "win32":
        import io
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    # Lê dados do stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Se não for JSON válido, retorna sucesso silenciosamente
        sys.exit(0)
    
    hook_event = input_data.get("hook_event_name", "")
    
    # Processa baseado no tipo de evento
    if hook_event == "UserPromptSubmit":
        result = handle_user_prompt(input_data)
    elif hook_event == "PostToolUse":
        result = handle_post_tool_use(input_data)
    elif hook_event == "SessionEnd":
        result = handle_session_end(input_data)
    else:
        result = None
    
    # Se houver resultado, imprime como JSON
    if result:
        print(json.dumps(result, ensure_ascii=False))
    
    sys.exit(0)

if __name__ == "__main__":
    main()