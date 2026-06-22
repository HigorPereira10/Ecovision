# EcoVision Cerrado

> **Sistema de Monitoramento IoT e Visão Computacional para o Controle Fitossanitário em Estufas**

Este é o repositório centralizado do projeto EcoVision, um sistema inteligente focado na deteção precoce de pragas e anomalias em culturas protegidas utilizando Inteligência Artificial e Internet das Coisas (IoT).

---

## 📌 Links Úteis do Projeto
* **Quadro de Tarefas (Kanban):** [Aceder ao GitHub Projects here](https://github.com/users/HigorPereira10/projects/1)
* **Comunicação da Equipa:** [Servidor do Discord]()
* **Documentação de Texto (TCC):** [Pasta Partilhada no Google Drive]()

---

## 📁 Estrutura de Pastas (Monorepo)

[cite_start]O projeto adota uma arquitetura de *monorepo*, concentrando todos os componentes do ecossistema numa única estrutura de diretórios[cite: 15]:

* [cite_start]`/app`: Contém o código-fonte do painel/dashboard mobile e web que será utilizado pelo produtor rural para visualizar os dados e diagnósticos[cite: 21, 51].
* [cite_start]`/cloud`: Repositório do backend desenvolvido em FastAPI, responsável por receber os dados, integrar o runtime do TFLite e expor as APIs de inferência e alertas[cite: 20, 48, 117].
* [cite_start]`/docs`: Centraliza toda a documentação técnica, atas de reuniões e os capítulos da escrita académica do TCC[cite: 25, 26].
* [cite_start]`/edge`: Código-fonte que será executado localmente no Raspberry Pi Zero 2 W, incluindo os scripts de captura de imagem (Picamera2), leitura de sensores (DHT22/ADS1115) e cache offline[cite: 17, 18, 44, 45, 63].
* [cite_start]`/infra`: Scripts de automatização, ficheiros de configuração de ambiente e diretivas de deploy para as plataformas Railway e Supabase[cite: 27, 28].
* [cite_start]`/ml`: Pipeline de Machine Learning completo, contendo os notebooks do Google Colab, rotinas de preparação do dataset, treino da MobileNetV2 e conversão de modelos para o formato TFLite[cite: 23, 24, 41].

---

## 🛠️ Metodologia de Trabalho & Gestão

[cite_start]O desenvolvimento é guiado por um framework ágil baseado num Scrum Simplificado, estruturado em sprints de 2 semanas[cite: 4, 7].

### GitHub Projects
[cite_start]Toda a distribuição de atividades é centralizada no **GitHub Projects** através de um quadro Kanban composto por três esteiras principais[cite: 29, 30]:
1. **Todo (A Fazer):** Lista de tarefas priorizadas para a sprint atual.
2. **In Progress (Em Progresso):** Atividades ativas sendo desenvolvidas por um membro da equipa.
3. **Done (Concluído):** Tarefas finalizadas e validadas.

[cite_start]Cada atividade é mapeada como uma *Issue* e deve obrigatoriamente conter um responsável (*Assignee*) e uma etiqueta (*Label*) correspondente ao seu componente (`edge`, `cloud`, `app`, `ml` ou `docs`)[cite: 30].

---

## 🌿 Fluxo de Desenvolvimento (Branch Policy)

Para garantir a estabilidade do sistema e evitar conflitos no código principal, adotamos uma política rigorosa de branches ("Acordo de Cavalheiros"):

1. [cite_start]**A branch `main` é sagrada:** É estritamente proibido realizar commits diretos na branch `main`[cite: 31].
2. [cite_start]**Criação de Branches:** Toda e qualquer tarefa iniciada a partir do quadro Kanban deve possuir uma branch isolada utilizando o padrão de nomenclatura do componente (ex: `feature/edge-camera-capture`, `feature/cloud-fastapi-inference`)[cite: 31].
3. **Pull Requests & Code Review:** Ao concluir uma funcionalidade, o desenvolvedor deve abrir um *Pull Request* direcionado à `main`. [cite_start]O merge só será realizado após a revisão e aprovação de, pelo menos, **1 outro integrante da equipa**[cite: 32].
