import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryChart, VictoryLine, VictoryAxis } from 'victory-native';
import { colors } from '../theme/colors';
import { LeituraAmbiental } from '../services/leituras';

/**
 * Condições da estufa ao longo do tempo, em um gráfico por variável.
 *
 * Gráficos separados evitam que a temperatura, de faixa estreita, vire uma
 * linha reta ao dividir o eixo com a umidade, e evitam o eixo duplo, que
 * sugere correlação. As cores seguem os cartões de leitura do Dashboard
 * (laranja para temperatura, azul para umidade do ar, verde para umidade
 * do solo).
 *
 * Cada gráfico tem uma linha de referência com a origem indicada: para
 * temperatura e umidade do ar, o limite de referência na mesma unidade do
 * sensor (traço curto); para o solo, a capacidade de campo medida no vaso,
 * na escala do sensor (traço longo), já que o sensor não mede as grandezas
 * usadas nos critérios de irrigação.
 */

interface SerieTemporalCardProps {
  leituras: LeituraAmbiental[]; // ordenadas por timestamp crescente
}

/** Umidade do ar acima da qual a folha permanece úmida por mais tempo,
 * favorecendo mofo. É o mesmo limiar do alerta ambiental do servidor. */
const LIMIAR_UMIDADE_PCT = 90;

/** Tolerância ampla do tomateiro, fora da qual há risco de perda
 * rápida. */
const FAIXA_TEMPERATURA_C = { min: 10, max: 34 };

/** Capacidade de campo do vaso monitorado, na escala do sensor (espelha
 * CAPACIDADE_DE_CAMPO_MEDIDA_PCT em cloud/app/core/alertas_ambientais.py).
 *
 * Identificada pelo patamar de seis horas (75,7% a 76,2%) que seguiu a
 * drenagem de uma rega, em uma única medição. Acima dela, o solo está
 * drenando; abaixo, começou a secar. Não é uma recomendação de irrigação:
 * os critérios publicados usam tensão (15 a 25 kPa; BRAGA; FELTRIM;
 * BORGES, 2022) ou fração de água disponível (FAO-56, Tabela 22), e
 * exigem também o ponto de murcha permanente. */
const CAPACIDADE_DE_CAMPO_PCT = 76;

/** Limiares de alerta do servidor (UMIDADE_SOLO_MIN_PCT e MAX em
 * cloud/app/core/alertas_ambientais.py), que não são desenhados.
 *
 * O máximo aparece na legenda, para explicar por que o solo entre a
 * capacidade de campo (76%) e 80% não gera alerta. O mínimo não aparece
 * nesta tela por não ter respaldo agronômico e ficar fora da faixa em que
 * o vaso opera; ele é exibido na tela de Perfil. */
const FAIXA_SOLO_PCT = { min: 20, max: 80 };

/** Tensão crítica de irrigação para tomate de mesa, em kPa (Braga,
 * Feltrim e Borges, 2022, p. 105), citada no rodapé do cartão. */
const TENSAO_CRITICA_KPA = { min: 15, max: 25 };

/** Fração de água disponível a manter no solo, da FAO-56 (p = 0,40 para
 * tomate, logo 1 - 0,40), citada no rodapé do cartão. */
const AGUA_DISPONIVEL_MINIMA_PCT = 60;

/** Leituras abaixo deste valor estão no piso da escala e indicam sonda
 * fora da terra ou calibração pendente, não solo seco (espelha
 * SOLO_PISO_SUSPEITO_PCT no servidor). */
const PISO_SUSPEITO_SOLO_PCT = 4;

const FONTE_CLIMA = 'Embrapa Hortaliças, Tomate de mesa: Clima';

/**
 * Temperatura e umidade exatamente zero indicam falha do DHT22, não
 * medição; essas leituras ficam no banco, mas não são desenhadas.
 */
function ehFalhaDoSensor(l: LeituraAmbiental): boolean {
  return l.temperatura === 0 && l.umidade_ar === 0;
}

export function SerieTemporalCard({ leituras }: SerieTemporalCardProps) {
  const validas = leituras.filter((l) => !ehFalhaDoSensor(l));

  // Cada série ignora os pontos sem medição própria (null quando o sensor
  // falhou); se só a umidade falhou, a temperatura do ciclo continua.
  const dadosTemperatura = validas
    .filter((l) => l.temperatura !== null)
    .map((l) => ({ x: new Date(l.timestamp), y: l.temperatura as number }));

  const dadosUmidade = validas
    .filter((l) => l.umidade_ar !== null)
    .map((l) => ({ x: new Date(l.timestamp), y: l.umidade_ar as number }));

  // Leituras de solo no piso da escala não são medição e saem da série.
  const leiturasSolo = validas.filter((l) => l.umidade_solo !== null);
  const dadosSolo = leiturasSolo
    .filter((l) => (l.umidade_solo as number) > PISO_SUSPEITO_SOLO_PCT)
    .map((l) => ({ x: new Date(l.timestamp), y: l.umidade_solo as number }));
  const soloNoPiso = leiturasSolo.length - dadosSolo.length;

  // Com menos de dois pontos não há linha: exibe uma frase explicativa em
  // vez de um gráfico vazio.
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
          tipo: 'recomendacao',
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
          tipo: 'recomendacao',
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
          valor: CAPACIDADE_DE_CAMPO_PCT,
          tipo: 'medido',
          texto:
            'É onde a água para de drenar neste vaso, medido em 03/11. Acima da ' +
            'linha o solo tem mais água do que consegue reter, e os poros ficam ' +
            `sem ar para a raiz: o sistema avisa a partir de ${FAIXA_SOLO_PCT.max}%. ` +
            'Abaixo da linha o solo está secando, e quanto mais longe, mais seco.',
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
        Temperatura e umidade do ar: {FONTE_CLIMA}, e a linha tracejada é a
        própria recomendação.
      </Text>
      <Text style={styles.fonte}>
        Solo: a linha de {CAPACIDADE_DE_CAMPO_PCT}% é a capacidade de campo
        medida neste vaso em 03/11/2026, pelo patamar de 6 horas que seguiu a
        drenagem de uma rega. Não é recomendação de quando irrigar: os critérios
        publicados usam outras unidades, {TENSAO_CRITICA_KPA.min}-
        {TENSAO_CRITICA_KPA.max} kPa de tensão (Braga, Feltrim e Borges,
        Irrigação, cap. 7 de Produção integrada do tomateiro tutorado, UFV/CEAD,
        2022, p. 105) e {AGUA_DISPONIVEL_MINIMA_PCT}% da água disponível (FAO-56,
        Tabela 22), e os dois exigem o ponto de murcha permanente, que ainda não
        foi medido.
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
  referencia: {
    valor: number;
    texto: string;
    /** Origem do número da linha, que define o traço e o texto:
     * 'recomendacao' = referência publicada na unidade do sensor (traço
     * curto); 'medido' = medição feita no vaso monitorado (traço longo). */
    tipo: 'recomendacao' | 'medido';
  };
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

  // O domínio sempre inclui a linha de referência, para mostrar a margem
  // mesmo quando as medições estão longe dela.
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
              strokeDasharray:
                referencia.tipo === 'recomendacao' ? '4,4' : '8,4',
            },
          }}
        />
        <VictoryLine data={dados} style={{ data: { stroke: cor, strokeWidth: 2 } }} />
      </VictoryChart>

      <Text style={styles.serieLegenda}>
        {referencia.tipo === 'recomendacao'
          ? `A linha tracejada marca ${referencia.valor} ${unidade}, recomendado. `
          : `A linha tracejada marca ${referencia.valor} ${unidade}, medido nesta estufa. `}
        {referencia.texto}
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
