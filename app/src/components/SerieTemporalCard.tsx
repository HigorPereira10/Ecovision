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

  // Uma linha precisa de DOIS pontos para existir. Com um ponto só, o
  // gráfico saía desenhado, com eixos e grade, e completamente vazio
  // por dentro, enquanto o eixo do tempo repetia o mesmo horário cinco
  // vezes (foi o que apareceu no primeiro teste com o dispositivo real:
  // "16:50" cinco vezes e nenhuma linha). Um gráfico vazio parece
  // defeito; uma frase explicando o que falta, não.
  const pontosSuficientes = dadosTemperatura.length >= 2 || dadosUmidade.length >= 2;

  if (!pontosSuficientes) {
    const algumaMedicao = dadosTemperatura.length > 0 || dadosUmidade.length > 0;
    return (
      <View style={styles.card}>
        <Text style={styles.titulo}>Condições da estufa</Text>
        <Text style={styles.subtitulo}>
          {leituras.length === 0
            ? 'Nenhuma leitura recebida ainda.'
            : algumaMedicao
              ? 'Só há uma medição até agora. O gráfico aparece a partir da segunda.'
              : 'As leituras recebidas não trazem temperatura nem umidade do ar.'}
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
        cor={colors.oliveGreen}
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
        cor={colors.danger}
        largura={largura}
        referencia={{
          valor: FAIXA_TEMPERATURA_C.max,
          texto: `O tomateiro tolera de ${FAIXA_TEMPERATURA_C.min} a ${FAIXA_TEMPERATURA_C.max} °C. Fora dessa faixa há risco de perda rápida.`,
        }}
      />

      <Text style={styles.fonte}>Faixas recomendadas: {FONTE}.</Text>
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
}

function MiniSerie({
  titulo,
  unidade,
  dados,
  cor,
  largura,
  referencia,
}: MiniSerieProps) {
  if (dados.length < 2) {
    return (
      <View style={styles.serie}>
        <Text style={styles.serieTitulo}>{titulo}</Text>
        <Text style={styles.serieVazia}>Sem medição suficiente.</Text>
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
  fonte: {
    fontSize: 10,
    color: colors.textMuted,
    fontStyle: 'italic',
    marginTop: 2,
  },
});
