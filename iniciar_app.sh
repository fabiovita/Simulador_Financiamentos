#!/bin/bash
cd "$(dirname "$0")/app"

# O python3 do PATH nem sempre é o que tem streamlit instalado (Homebrew x Python.framework).
# Usa o primeiro interpretador que consiga importar streamlit; PYTHON=... sobrescreve.
CANDIDATOS=(
    "$PYTHON"
    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
    "$(command -v python3)"
)

for candidato in "${CANDIDATOS[@]}"; do
    if [ -x "$candidato" ] && "$candidato" -c "import streamlit" 2>/dev/null; then
        exec "$candidato" -m streamlit run app.py
    fi
done

echo "Erro: nenhum python3 com streamlit instalado."
echo "Instale as dependências com: python3 -m pip install -r requirements.txt"
echo "Ou aponte o interpretador certo: PYTHON=/caminho/para/python3 ./iniciar_app.sh"
exit 1
