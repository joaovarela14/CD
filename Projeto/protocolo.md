
# Protocolo de Comunicação do Projeto Sudoku

---

Este documento descreve o protocolo de comunicação utilizado no projeto Sudoku, incluindo a interação entre os componentes do sistema e a troca de mensagens. O projeto inclui um servidor central que gere a resolução de puzzles Sudoku e vários nós que colaboram para resolver partes do Sudoku de forma distribuída. Cada componente (`node.py`, `server.py`, e `sudoku.py`) tem um papel específico na arquitetura distribuída, facilitando a comunicação, administração e execução de tarefas específicas.

---

## 1. Visão Geral do Sistema

O sistema é composto por três componentes principais:
1. **Servidor Central (`server.py`)**: Recebe solicitações de clientes para resolver puzzles Sudoku, coordena a resolução distribuída e retorna os resultados.
2. **Worker Node (`node.py`)**: Resolve partes do Sudoku e comunica-se com outros nós e com o servidor central para colaborar na resolução distribuída.
3. **Classe Sudoku (`sudoku.py`)**: Fornece funcionalidades para representar e resolver puzzles Sudoku.

## 2. Estrutura de Mensagens

As mensagens entre o servidor central e os worker nodes são codificadas em JSON e transmitidas via sockets TCP. A estrutura básica de uma mensagem inclui um tipo de mensagem e os dados associados.

### Exemplo de Estrutura de Mensagem:
\`\`\`json
{
    "type": "tipo_de_mensagem",
    "data": {
        "chave1": "valor1",
        "chave2": "valor2",
        ...
    }
}
\`\`\`

## 3. Tipos de Mensagens

### 3.1. Mensagens Enviadas pelo Servidor Central

- **\`solve\`**:
  - **Descrição**: Solicita a resolução de um puzzle Sudoku.
  - **Destino**: Worker Node.
  - **Formato**:
    \`\`\`json
    {
        "type": "solve",
        "data": {
            "sudoku": [[8, 2, 7, 1, 5, 4, 3, 9, 6], ...]  // Sudoku completo
        }
    }
    \`\`\`

- **\`stats\`**:
  - **Descrição**: Solicita estatísticas de desempenho dos nós.
  - **Destino**: Worker Node.
  - **Formato**:
    \`\`\`json
    {
        "type": "stats"
    }
    \`\`\`

- **\`network\`**:
  - **Descrição**: Solicita informações sobre a rede de nós.
  - **Destino**: Worker Node.
  - **Formato**:
    \`\`\`json
    {
        "type": "network"
    }
    \`\`\`

### 3.2. Mensagens Enviadas pelos Worker Nodes

- **\`join\`**:
  - **Descrição**: Solicita a entrada na rede de nós.
  - **Destino**: Anchor node ou outro Worker node.
  - **Formato**:
    \`\`\`json
    {
        "type": "join",
        "address": "127.0.0.1:7001"
    }
    \`\`\`

- **\`solve_part\`**:
  - **Descrição**: Envia uma parte do Sudoku para ser resolvida.
  - **Destino**: Worker Node.
  - **Formato**:
    \`\`\`json
    {
        "type": "solve_part",
        "part_index": 0,
        "part": [[5, 0, 3, 4, 6, 8, 2, 7, 1], ...]
    }
    \`\`\`

## 4. Protocolo de Comunicação

### 4.1. Inicialização de Conexão

1. **Solicitação de Entrada na Rede**:
   - Quando um worker node é iniciado, ele automaticamente tenta juntar-se à rede de nós existentes. Ele faz isso enviando uma mensagem de join ao anchor node.
   
2. **Processamento da Solicitação join:**:
   - O anchor node recebe a solicitação de join e adiciona o novo nó à sua lista de nós conhecidos. Este nó, então, responde com a lista atualizada de todos os nós na rede, permitindo que o novo nó tenha conhecimento de todos os outros nós presentes.
   
3. **Atualização de Rede**:
   - Cada nó mantém uma lista dos nós conhecidos e atualiza essa lista sempre que um novo nó entra na rede. Esta lista é usada para facilitar a comunicação e a distribuição de tarefas entre os nós.

### 4.2. Resolução de Sudoku

1. **Distribuição de Tarefas**:
   - O servidor ou node  envia uma mensagem \`solve\` para os worker nodes, contendo o Sudoku completo.
   - O Sudoku é dividido em partes, e cada nó resolve a sua parte.

2. **Recolha e Combinação de Resultados**:
   - Cada nó retorna as suas soluções parciais.
   - O servidor ou node combina as soluções parciais para formar a solução completa do Sudoku.

3. **Verificação de Soluções**:
   - As soluções são verificadas para garantir que sejam válidas antes de serem aceites como solução final. Assim que é encontrada uma solução válida esta é retornada.

### 4.3. Recolha de Estatísticas

1. **Solicitação de Estatísticas**:
   - O servidor central ou node  envia uma mensagem \`stats\` para cada worker node.
   - Cada nó retorna as suas estatísticas de desempenho, como o número de Sudoku resolvidos e o número de validações realizadas.

2. **Consolidação de Dados**:
   - O servidor recolhe todas as estatísticas e consolida os dados para análise.

### 4.4. Gestão da Rede

1. **Solicitação de Informações da Rede**:
   - O servidor ou qualquer nó pode solicitar a lista de nós atuais enviando uma mensagem \`network\`.
   - Cada nó retorna a lista de nós conhecidos, facilitando a manutenção e expansão da rede.

## 5. Conclusão

O protocolo de comunicação descrito neste documento garante a coordenação eficaz entre os componentes do sistema de resolução de Sudoku, permitindo uma solução distribuída e eficiente dos puzzles Sudoku. A comunicação em JSON e o uso de sockets TCP facilitam a expansão e manutenção do sistema.

