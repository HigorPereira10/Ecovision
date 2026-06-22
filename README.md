# EcoVision Cerrado

> **Sistema de Monitoramento IoT e Visão Computacional para o Controle Fitossanitário em Estufas**

Este é o repositório centralizado do projeto EcoVision, um sistema inteligente focado na detecção precoce de pragas e anomalias em culturas protegidas utilizando Inteligência Artificial e Internet das Coisas (IoT).

---

## 📌 Links Úteis do Projeto
* **Quadro de Tarefas (Kanban):** [GitHub Projects](https://github.com/users/HigorPereira10/projects/1)
* **Comunicação da Equipa:** [Servidor do Discord]()
* **Documentação de Texto (TCC):** [Pasta Partilhada no Google Drive]()

---

## 📁 Estrutura de Pastas (Monorepo)

O projeto adota uma arquitetura de *monorepo*, concentrando todos os componentes do ecossistema numa única estrutura de diretórios:

* `/app`: Contém o código-fonte do painel/dashboard mobile e web que será utilizado pelo produtor rural para visualizar os dados e diagnósticos.
* `/cloud`: Repositório do backend desenvolvido em FastAPI, responsável por receber os dados, integrar o runtime do TFLite e expor as APIs de inferência e alertas.
* `/docs`: Centraliza toda a documentação técnica, atas de reuniões e os capítulos da escrita académica do TCC.
* `/edge`: Código-fonte que será executado localmente no Raspberry Pi Zero 2 W, incluindo os scripts de captura de imagem (Picamera2), leitura de sensores (DHT22/ADS1115) e cache offline.
* `/infra`: Scripts de automatização, ficheiros de configuração de ambiente e diretivas de deploy para as plataformas Railway e Supabase.
* `/ml`: Pipeline de Machine Learning completo, contendo os notebooks do Google Colab, rotinas de preparação do dataset, treino da MobileNetV2 e conversão de modelos para o formato TFLite.

---

## 🛠️ Metodologia de Trabalho & Gestão

O desenvolvimento é guiado por um framework ágil baseado num Scrum Simplificado, estruturado em sprints de 2 semanas.

### GitHub Projects
[cite_start]Toda a distribuição de atividades é centralizada no **GitHub Projects** através de um quadro Kanban composto por três esteiras principais:
1. **Todo (A Fazer):** Lista de tarefas priorizadas para a sprint atual.
2. **In Progress (Em Progresso):** Atividades ativas sendo desenvolvidas por um membro da equipa.
3. **Done (Concluído):** Tarefas finalizadas e validadas.

Cada atividade é mapeada como uma *Issue* e deve obrigatoriamente conter um responsável (*Assignee*) e uma etiqueta (*Label*) correspondente ao seu componente (`edge`, `cloud`, `app`, `ml` ou `docs`).

---

## 🌿 Fluxo de Desenvolvimento (Branch Policy)

Para garantir a estabilidade do sistema e evitar conflitos no código principal, adotamos uma política rigorosa de branches ("Acordo de Cavalheiros"):

1. **A branch `main` é sagrada:** É estritamente proibido realizar commits diretos na branch `main`.
2. **Criação de Branches:** Toda e qualquer tarefa iniciada a partir do quadro Kanban deve possuir uma branch isolada utilizando o padrão de nomenclatura do componente (ex: `feature/edge-camera-capture`, `feature/cloud-fastapi-inference`).
3. **Pull Requests & Code Review:** Ao concluir uma funcionalidade, o desenvolvedor deve abrir um *Pull Request* direcionado à `main`. [cite_start]O merge só será realizado após a revisão e aprovação de, pelo menos, **1 outro integrante da equipa**.
