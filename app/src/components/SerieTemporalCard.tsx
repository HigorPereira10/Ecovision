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
 * CADA GRÁFICO MOSTRA O SEU LIMIAR, E CITA DE ONDE ELE VEIO
 * ---------------------------------------------------------
 * É o que transforma o cartão de decorativo em informativo: a linha de
 * referência responde "isto está bom?" sem o produtor precisar decorar
 * número nenhum.
 *
 * Temperatura e umidade do ar vêm da Embrapa Hortaliças (ver
 * LIMIAR_UMIDADE_PCT e FAIXA_TEMPERATURA_C), na mesma unidade que o
 * sensor mede, então a linha tracejada É a recomendação.
 *
 * O solo é o caso difícil, e está explicado por inteiro em
 * FAIXA_SOLO_PCT: o sensor foi calibrado entre ar seco e água pura, e os
 * dois critérios publicados estão em unidades diferentes dessa (kPa de
 * tensão e fração de água disponível). Então a linha do solo tem traço
 * PONTILHADO e a legenda diz que ela marca onde o nosso alerta dispara,
 * não o que alguém recomenda. As duas fontes ficam citadas no pé.
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

/** Limite de alerta do solo, igual ao do servidor
 * (UMIDADE_SOLO_MIN_PCT em cloud/app/core/alertas_ambientais.py).
 *
 * ESTE NÚMERO NÃO É RECOMENDAÇÃO AGRONÔMICA, E A DIFERENÇA IMPORTA
 * ----------------------------------------------------------------
 * Nas duas séries acima, a linha tracejada É a recomendação: o limiar e
 * a fonte estão na mesma unidade, graus e porcentagem de umidade
 * relativa do ar. Aqui não, e colocar as três linhas com a mesma cara
 * faria o olho ler a nossa invenção com o mesmo peso da Embrapa.
 *
 * O que esta linha marca é o ponto em que o SISTEMA dispara o alerta de
 * solo seco. Ela fica visível porque o alerta existe de verdade e
 * gatilho que dispara invisível é pior do que gatilho mal justificado,
 * mas a legenda diz o que ela é.
 *
 * POR QUE NÃO DÁ PARA USAR O NÚMERO DE NINGUÉM AQUI
 * -------------------------------------------------
 * O sensor foi calibrado suspenso no AR (17468 bruto) e submerso em
 * ÁGUA PURA (7179), ver edge/src/config.py, onde isso já está marcado
 * como pendência. Então os 0-100% significam "umidade relativa entre ar
 * seco e submerso", que não é nenhuma das grandezas em que a literatura
 * agronômica mede água no solo: não é tensão, não é umidade volumétrica
 * e não é fração de água disponível.
 *
 * Não é falta de fonte. São duas, e as duas estão citadas no pé do
 * cartão:
 *
 *   TENSÃO. Para tomate de mesa tutorado, irrigar quando a tensão da
 *   água no solo chega a 15-25 kPa, medida com tensiômetro (15 kPa nos
 *   10 a 20 dias após o transplante, 25 kPa depois).
 *     BRAGA, M.B.; FELTRIM, A.L.; BORGES, L.C. Irrigação. In: ZAMBOLIM,
 *     L.; QUEZADO-DUVAL, A.M. (org.). Produção integrada do tomateiro
 *     tutorado. Viçosa, MG: UFV, CEAD, 2022. cap. 7, p. 102-116.
 *
 *   FRAÇÃO DE ÁGUA DISPONÍVEL. Tomate tem p = 0,40, ou seja, irrigar
 *   quando 40% da água disponível foi consumida, mantendo o solo acima
 *   de 60% dela.
 *     ALLEN, R.G. et al. Crop evapotranspiration: guidelines for
 *     computing crop water requirements. Roma: FAO, 1998. (FAO
 *     Irrigation and Drainage Paper, 56). Tabela 22.
 *
 * O CAMINHO PARA ESTA LINHA VIRAR RECOMENDAÇÃO DE VERDADE
 * -------------------------------------------------------
 * A segunda fonte é a que dá o alvo, porque está em porcentagem. Se
 * SOIL_DRY_RAW for recalibrado no PONTO DE MURCHA PERMANENTE e
 * SOIL_WET_RAW na CAPACIDADE DE CAMPO, em vez de ar e água, os 0-100%
 * do sensor passam a aproximar "porcentagem de água disponível", e o
 * limiar passa a ser 60%, citável direto da FAO-56. Ver
 * docs/decisions/0005-limiares-ambientais.md, seção de calibração. */
const FAIXA_SOLO_PCT = { min: 20, max: 80 };

/** Tensão crítica de irrigação para tomate de mesa, em kPa (Braga,
 * Feltrim e Borges, 2022, p. 105). Não entra em comparação nenhuma: o
 * sensor não mede kPa. Está aqui para a legenda citar o critério. */
const TENSAO_CRITICA_KPA = { min: 15, max: 25 };

/** Fração de água disponível a manter no solo, da FAO-56 (p = 0,40 para
 * tomate, logo 1 - 0,40). Também não entra em comparação: é o alvo da
 * recalibração descrita acima.
 *
 * A FAO-56 ainda corrige p pela evapotranspiração,
 * p = 0,40 + 0,04 (5 - ETc), limitado a 0,1 <= p <= 0,8. Numa estufa
 * quente o ETc passa de 5 mm/dia, p cai e o piso sobe acima de 60%.
 * Esse refinamento fica para depois da calibração: sem ela, aplicar a
 * correção seria precisão decorativa sobre um número que ainda não
 * mede a grandeza certa. */
const AGUA_DISPONIVEL_MINIMA_PCT = 60;

/** Abaixo disso a leitura do solo está no piso da escala, o que indica
 * sonda fora da terra ou calibração pendente, não solo seco. Espelha
 * SOLO_PISO_SUSPEITO_PCT no servidor, que gera alerta de sensor em vez
 * de alerta de seca. Com a sonda fora do vaso, as leituras ficaram em
 * 1,7 a 2,1%. */
const PISO_SUSPEITO_SOLO_PCT = 4;

const FONTE_CLIMA = 'Embrapa Hortaliças, Tomate de mesa: Clima';

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
          valor: FAIXA_SOLO_PCT.min,
          tipo: 'alerta',
          texto:
            `É onde o sistema avisa que o solo está seco, e acima de ` +
            `${FAIXA_SOLO_PCT.max}% que está encharcado. Não é recomendação ` +
            'agronômica: este sensor foi calibrado entre ar seco e água, então mede ' +
            'umidade relativa, não a tensão nem a água disponível que a literatura ' +
            'usa. Os critérios publicados estão citados abaixo.',
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
        Solo: os critérios publicados são {TENSAO_CRITICA_KPA.min}-
        {TENSAO_CRITICA_KPA.max} kPa de tensão (Braga, Feltrim e Borges,
        Irrigação, cap. 7 de Produção integrada do tomateiro tutorado, UFV/CEAD,
        2022, p. 105) e manter acima de {AGUA_DISPONIVEL_MINIMA_PCT}% da água
        disponível (FAO-56, Tabela 22, p = 0,40 para tomate). A linha de{' '}
        {FAIXA_SOLO_PCT.min}% é o limite de alerta deste sistema, pendente de
        calibração contra esses critérios.
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
    /** 'recomendacao' = o limiar vem de fonte publicada, na mesma unidade
     * que o sensor mede, e a linha É a recomendação (traço largo).
     * 'alerta' = o limiar é deste sistema, a fonte publicada usa outra
     * unidade, e a linha só marca onde o nosso alerta dispara (traço
     * pontilhado). A diferença de traço existe para o olho não ler as
     * duas com o mesmo peso. */
    tipo: 'recomendacao' | 'alerta';
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
              strokeDasharray:
                referencia.tipo === 'recomendacao' ? '4,4' : '1,3',
            },
          }}
        />
        <VictoryLine data={dados} style={{ data: { stroke: cor, strokeWidth: 2 } }} />
      </VictoryChart>

      <Text style={styles.serieLegenda}>
        {referencia.tipo === 'recomendacao'
          ? `A linha tracejada marca ${referencia.valor} ${unidade}, recomendado. `
          : `A linha pontilhada marca ${referencia.valor} ${unidade}. `}
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
