import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryChart, VictoryLine, VictoryAxis } from 'victory-native';
import { colors } from '../theme/colors';
import { LeituraAmbiental } from '../services/leituras';

/**
 * Condições da estufa ao longo do tempo.
 *
 * POR QUE DOIS GRÁFICOS E NÃO UM
 * ------------------------------
 * Até 2026-11-02 as duas séries dividiam o mesmo eixo Y. Com os dados
 * reais do dispositivo, a temperatura ia de 20,8 a 28,4 °C e a umidade
 * de 64,3 a 79,2 %: num eixo de 21 a 79, a variação da temperatura
 * ocupava 13% da altura e virava uma linha quase reta colada embaixo.
 * Sete graus de variação numa estufa desapareciam.
 *
 * Também não havia legenda: duas linhas coloridas e nada dizendo qual
 * era qual.
 *
 * Separar resolve os dois problemas de uma vez, e evita o eixo duplo,
 * que sugere correlação entre as séries sem que ela tenha sido medida.
 *
 * AS CORES SÃO AS DOS CARDS LOGO ACIMA
 * -------------------------------------
 * Laranja para temperatura, azul para umidade do ar, verde para umidade
 * do solo: exatamente o que LeituraCard usa no Dashboard. Antes o
 * gráfico pintava a umidade do ar de verde, que é a cor do SOLO na
 * linha de cards imediatamente acima dele, na mesma tela. Trocar a cor
 * de significado no meio da rolagem é pior do que não ter cor.
 *
 * CADA GRÁFICO MOSTRA O SEU LIMIAR
 * --------------------------------
 * É o que transforma o cartão de decorativo em informativo: a linha de
 * referência responde "isto está bom?" sem o produtor precisar decorar
 * número nenhum. Os limiares e as frases vêm da Embrapa Hortaliças (ver
 * LIMIAR_UMIDADE_PCT e FAIXA_TEMPERATURA_C).
 */

interface SerieTemporalCardProps {
  leituras: LeituraAmbiental[]; // ordenadas por timestamp crescente
}

/** Acima disso a Embrapa associa surgimento de mofo nas folhas. É o
 * mesmo limiar que o servidor usa para alerta ambiental e para estimar
 * molhamento foliar no cruzamento com o diagnóstico. */
const LIMIAR_UMIDADE_PCT = 90;

/** Tolerância ampla do tomateiro, fora da qual há risco de perda
 * rápida. */
const FAIXA_TEMPERATURA_C = { min: 10, max: 34 };

/** Faixa de conforto do solo. ATENÇÃO: diferente das duas acima, este
 * número NÃO vem da Embrapa. É a mesma convenção prática que o servidor
 * usa (UMIDADE_SOLO_MIN_PCT em cloud/app/core/alertas_ambientais.py),
 * registrada lá com a ressalva de que depende do substrato e da
 * calibração do sensor resistivo.
 *
 * Por isso a nota de fonte no pé do cartão fala só de temperatura e
 * umidade do ar, e a ressalva do solo vai na legenda da própria série.
 * Pendurar um número nosso na credibilidade da Embrapa é o tipo de coisa
 * que a banca cobra e que não tem defesa. */
const FAIXA_SOLO_PCT = { min: 20, max: 80 };

/** Abaixo disso a leitura do solo está no piso da escala, o que indica
 * sonda fora da terra ou calibração pendente, não solo seco. Espelha
 * SOLO_PISO_SUSPEITO_PCT no servidor, que gera alerta de sensor em vez
 * de alerta de seca. Com a sonda fora do vaso, as leituras ficaram em
 * 1,7 a 2,1%. */
const PISO_SUSPEITO_SOLO_PCT = 4;

const FONTE = 'Embrapa Hortaliças, Tomate de mesa: Clima';

/**
 * Leitura em que temperatura E umidade vêm exatamente zero não é
 * medição: é a assinatura de falha do DHT22, que passou a devolver
 * 0,0 nos dois campos em vez de erro. Três leituras assim ficaram no
 * banco (01/11, 00:30 às 00:50), de antes da guarda entrar no
 * dispositivo.
 *
 * Elas não são apagadas do banco, porque são registro de uma falha
 * real. Mas plotadas despencam o eixo e fazem parecer que a estufa
 * congelou, então saem daqui.
 */
function ehFalhaDoSensor(l: LeituraAmbiental): boolean {
  return l.temperatura === 0 && l.umidade_ar === 0;
}

export function SerieTemporalCard({ leituras }: SerieTemporalCardProps) {
  const validas = leituras.filter((l) => !ehFalhaDoSensor(l));

  // Cada série pula os pontos sem medição própria (a API devolve null
  // quando aquele sensor falhou no ciclo). O filtro é por série, não por
  // leitura: se só a umidade falhou, a temperatura do mesmo ciclo
  // continua sendo plotada.
  const dadosTemperatura = validas
    .filter((l) => l.temperatura !== null)
    .map((l) => ({ x: new Date(l.timestamp), y: l.temperatura as number }));

  const dadosUmidade = validas
    .filter((l) => l.umidade_ar !== null)
    .map((l) => ({ x: new Date(l.timestamp), y: l.umidade_ar as number }));

  // Leitura de solo no piso da escala sai da série pelo mesmo motivo que
  // o zero do DHT22: não é medição. Plotada contra a linha de 20% ela
  // desenha uma estufa em seca severa quando o que houve foi a sonda
  // fora da terra.
  const leiturasSolo = validas.filter((l) => l.umidade_solo !== null);
  const dadosSolo = leiturasSolo
    .filter((l) => (l.umidade_solo as number) > PISO_SUSPEITO_SOLO_PCT)
    .map((l) => ({ x: new Date(l.timestamp), y: l.umidade_solo as number }));
  const soloNoPiso = leiturasSolo.length - dadosSolo.length;

  // Uma linha precisa de DOIS pontos para existir. Com um ponto só, o
  // gráfico saía desenhado, com eixos e grade, e completamente vazio
  // por dentro, enquanto o eixo do tempo repetia o mesmo horário cinco
  // vezes (foi o que apareceu no primeiro teste com o dispositivo real:
  // "16:50" cinco vezes e nenhuma linha). Um gráfico vazio parece
  // defeito; uma frase explicando o que falta, não.
  const pontosSuficientes =
    dadosTemperatura.length >= 2 || dadosUmidade.length >= 2 || dadosSolo.length >= 2;

  if (!pontosSuficientes) {
    const algumaMedicao =
      dadosTemperatura.length > 0 || dadosUmidade.length > 0 || dadosSolo.length > 0;
    return (
      <View style={styles.card}>
        <Text style={styles.titulo}>Condições da estufa</Text>
        <Text style={styles.subtitulo}>
          {leituras.length === 0
            ? 'Nenhuma leitura recebida ainda.'
            : algumaMedicao
              ? 'Só há uma medição até agora. O gráfico aparece a partir da segunda.'
              : 'As leituras recebidas não trazem nenhuma medição de temperatura ou umidade.'}
        </Text>
      </View>
    );
  }

  const largura = Dimensions.get('window').width - 64;

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Condições da estufa</Text>
      <Text style={styles.subtitulo}>
        O que os sensores mediram, comparado com a faixa recomendada para o
        tomateiro.
      </Text>

      <MiniSerie
        titulo="Umidade do ar"
        unidade="%"
        dados={dadosUmidade}
        cor={colors.azulUmidade}
        largura={largura}
        referencia={{
          valor: LIMIAR_UMIDADE_PCT,
          texto: `Acima de ${LIMIAR_UMIDADE_PCT}% a folha permanece úmida por mais tempo, o que favorece o surgimento de mofo.`,
        }}
      />

      <MiniSerie
        titulo="Temperatura"
        unidade="°C"
        dados={dadosTemperatura}
        cor={colors.laranjaTemperatura}
        largura={largura}
        referencia={{
          valor: FAIXA_TEMPERATURA_C.max,
          texto: `O tomateiro tolera de ${FAIXA_TEMPERATURA_C.min} a ${FAIXA_TEMPERATURA_C.max} °C. Fora dessa faixa há risco de perda rápida.`,
        }}
      />

      <MiniSerie
        titulo="Umidade do solo"
        unidade="%"
        dados={dadosSolo}
        cor={colors.oliveGreen}
        largura={largura}
        referencia={{
          valor: FAIXA_SOLO_PCT.min,
          texto:
            `Abaixo de ${FAIXA_SOLO_PCT.min}% há risco de estresse hídrico e acima de ` +
            `${FAIXA_SOLO_PCT.max}% de apodrecimento da raiz. Esta faixa é convenção ` +
            'prática, não recomendação publicada: o sensor resistivo não foi calibrado ' +
            'para este substrato, então leia a curva como tendência.',
        }}
        aviso={
          soloNoPiso > 0
            ? `${soloNoPiso} ${soloNoPiso === 1 ? 'leitura ficou' : 'leituras ficaram'} ` +
              `abaixo de ${PISO_SUSPEITO_SOLO_PCT}% e não entraram no gráfico: no piso da ` +
              'escala, o valor indica sonda fora da terra, não solo seco.'
            : undefined
        }
      />

      <Text style={styles.fonte}>
        Faixas recomendadas de temperatura e umidade do ar: {FONTE}. A faixa do
        solo é convenção prática do projeto.
      </Text>
    </View>
  );
}

interface MiniSerieProps {
  titulo: string;
  unidade: string;
  dados: { x: Date; y: number }[];
  cor: string;
  largura: number;
  referencia: { valor: number; texto: string };
  /** Ressalva sobre medições que esta série descartou. Aparece abaixo da
   * legenda, para o produtor não achar que faltou dado sem motivo. */
  aviso?: string;
}

function MiniSerie({
  titulo,
  unidade,
  dados,
  cor,
  largura,
  referencia,
  aviso,
}: MiniSerieProps) {
  if (dados.length < 2) {
    return (
      <View style={styles.serie}>
        <Text style={styles.serieTitulo}>{titulo}</Text>
        <Text style={styles.serieVazia}>Sem medição suficiente.</Text>
        {aviso !== undefined && <Text style={styles.serieAviso}>{aviso}</Text>}
      </View>
    );
  }

  const valores = dados.map((d) => d.y);
  const atual = valores[valores.length - 1];

  // O domínio inclui a linha de referência SEMPRE, mesmo quando as
  // medições estão longe dela. Sem isso a linha sai do gráfico
  // justamente quando a leitura é confortável, que é quando o produtor
  // mais precisa ver o quanto sobra de margem.
  const minimo = Math.min(...valores, referencia.valor);
  const maximo = Math.max(...valores, referencia.valor);
  const folga = Math.max((maximo - minimo) * 0.12, 1);

  return (
    <View style={styles.serie}>
      <View style={styles.serieCabecalho}>
        <View style={[styles.marcador, { backgroundColor: cor }]} />
        <Text style={styles.serieTitulo}>{titulo}</Text>
        <Text style={styles.serieValor}>
          {atual.toFixed(1)} {unidade}
        </Text>
      </View>

      <VictoryChart
        width={largura}
        height={140}
        padding={{ top: 8, bottom: 26, left: 40, right: 12 }}
        domain={{ y: [minimo - folga, maximo + folga] }}
      >
        <VictoryAxis
          tickCount={4}
          tickFormat={(t) =>
            new Date(t).toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
            })
          }
          style={{
            tickLabels: { fontSize: 9, fill: colors.textMuted },
            axis: { stroke: colors.textMuted },
          }}
        />
        <VictoryAxis
          dependentAxis
          tickCount={4}
          style={{
            tickLabels: { fontSize: 10, fill: colors.textMuted },
            axis: { stroke: colors.textMuted },
          }}
        />
        <VictoryLine
          data={[
            { x: dados[0].x, y: referencia.valor },
            { x: dados[dados.length - 1].x, y: referencia.valor },
          ]}
          style={{
            data: {
              stroke: colors.textMuted,
              strokeWidth: 1,
              strokeDasharray: '4,4',
            },
          }}
        />
        <VictoryLine data={dados} style={{ data: { stroke: cor, strokeWidth: 2 } }} />
      </VictoryChart>

      <Text style={styles.serieLegenda}>
        A linha tracejada marca {referencia.valor} {unidade}. {referencia.texto}
      </Text>

      {aviso !== undefined && <Text style={styles.serieAviso}>{aviso}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  titulo: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textDark,
  },
  subtitulo: {
    fontSize: 12,
    color: colors.textMuted,
    marginBottom: 12,
  },
  serie: {
    marginBottom: 14,
  },
  serieCabecalho: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 2,
  },
  marcador: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 6,
  },
  serieTitulo: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textDark,
    flex: 1,
  },
  serieValor: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textDark,
  },
  serieLegenda: {
    fontSize: 11,
    color: colors.textMuted,
    lineHeight: 15,
    marginTop: 2,
  },
  serieVazia: {
    fontSize: 12,
    color: colors.textMuted,
  },
  serieAviso: {
    fontSize: 11,
    color: colors.cuidado,
    lineHeight: 15,
    marginTop: 4,
  },
  fonte: {
    fontSize: 10,
    color: colors.textMuted,
    fontStyle: 'italic',
    marginTop: 2,
  },
});
