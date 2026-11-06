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
 * CAPACIDADE_DE_CAMPO_PCT. Resumo: o sensor foi calibrado entre ar seco
 * e água pura, então não mede nenhuma das grandezas em que a literatura
 * expressa água no solo. Mas a CAPACIDADE DE CAMPO deste vaso foi
 * medida, na escala do próprio sensor, e é ela que a linha marca. Traço
 * tracejado LONGO, para distinguir de recomendação publicada sem fingir
 * que é invenção nossa: é medição nossa, que é coisa diferente das duas.
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

/** Capacidade de campo DESTE vaso, na escala do próprio sensor.
 *
 * É o que a linha de referência da série de solo marca, e é medição, não
 * convenção. Espelha CAPACIDADE_DE_CAMPO_MEDIDA_PCT em
 * cloud/app/core/alertas_ambientais.py.
 *
 * COMO FOI MEDIDA, SEM EXPERIMENTO NOVO
 * -------------------------------------
 * O vaso foi regado em 2026-11-03 às 19:49. A série de 15 minutos
 * registrou:
 *
 *     19:49 ............ 90,5%  (bruto 8156, saturado)
 *     21:00 ............ 76,0%  (bruto 9648, drenagem livre cessou)
 *     21:00 a 03:15 .... 75,7 a 76,2%  (25 leituras, 6 HORAS de patamar)
 *     3 dias depois .... 67,6%  (queda lenta, por evapotranspiração)
 *
 * O patamar que segue o fim da drenagem livre é a capacidade de campo,
 * por definição. O protocolo manda cobrir o vaso para excluir
 * evaporação da medida; não foi coberto, mas a janela foi das 19:49 às
 * 03:15, de madrugada, e a variação líquida nas 6 horas foi ZERO. A
 * condição que a cobertura existe para garantir foi verificada no dado
 * em vez de assumida.
 *
 * Limitação: um evento de rega, não replicado. A próxima rega confirma
 * ou desmente, e é de graça.
 *
 * POR QUE ESTA LINHA, E NÃO O LIMIAR DE 20%
 * -----------------------------------------
 * Até 2026-11-06 a linha ficava em FAIXA_SOLO_PCT.min, o limiar de
 * alerta de seca. Dois problemas, os dois medidos em 367 leituras:
 *
 * 1. Os 20% estão FORA da faixa que o vaso visita (67% a 76%), então a
 *    linha nunca aparecia perto dos dados. Linha de referência que o
 *    dado não alcança não responde "isto está bom?", que é a única
 *    pergunta que ela existe para responder.
 * 2. Aquele número não tinha respaldo nenhum, e o alerta de solo seco
 *    nunca disparou uma vez.
 *
 * A capacidade de campo resolve os dois: está dentro da faixa de
 * operação, e significa algo verificável. Acima dela o solo não retém a
 * água, está drenando e os poros ficam sem ar para a raiz. Abaixo,
 * começou a secar.
 *
 * O QUE ESTA LINHA AINDA NÃO É
 * ----------------------------
 * Não é recomendação de quando irrigar. Os critérios publicados usam
 * outras unidades e os dois exigem o ponto de murcha permanente, que é
 * propriedade do solo e NÃO se extrai de uma curva de secagem:
 *
 *   TENSÃO. Para tomate de mesa tutorado, irrigar quando a tensão da
 *   água no solo chega a 15-25 kPa, medida com tensiômetro.
 *     BRAGA, M.B.; FELTRIM, A.L.; BORGES, L.C. Irrigação. In: ZAMBOLIM,
 *     L.; QUEZADO-DUVAL, A.M. (org.). Produção integrada do tomateiro
 *     tutorado. Viçosa, MG: UFV, CEAD, 2022. cap. 7, p. 102-116.
 *
 *   FRAÇÃO DE ÁGUA DISPONÍVEL. Tomate tem p = 0,40: irrigar quando 40%
 *   da água disponível foi consumida, mantendo acima de 60% dela.
 *     ALLEN, R.G. et al. Crop evapotranspiration: guidelines for
 *     computing crop water requirements. Roma: FAO, 1998. (FAO
 *     Irrigation and Drainage Paper, 56). Tabela 22.
 *
 * Com a capacidade de campo já medida, falta um ponto só para chegar
 * lá. Ver docs/decisions/0005-limiares-ambientais.md. */
const CAPACIDADE_DE_CAMPO_PCT = 76;

/** Limiares de alerta do servidor (UMIDADE_SOLO_MIN_PCT e MAX em
 * cloud/app/core/alertas_ambientais.py). Não são linha no gráfico.
 *
 * Só o `max` aparece, e na legenda, não como linha. Ele existe no texto
 * para fechar uma lacuna de 4 pontos: a linha marca a capacidade de
 * campo (76%) e o alerta dispara em 80%, então entre os dois o gráfico
 * mostra o solo acima da linha e o sistema fica calado. Sem a frase, o
 * produtor leria isso como alerta que falhou. Com ela, fica claro que
 * acima da capacidade de campo o solo está drenando, e que o aviso vem
 * quando passa de 80%.
 *
 * O `min` (20%) NÃO aparece em lugar nenhum desta tela de propósito: ele
 * não tem respaldo, nunca disparou em 367 leituras e está fora da faixa
 * que o vaso visita. Mostrá-lo seria dar ao produtor um número em que
 * não se pode confiar. Ele continua visível na tela de Perfil, que
 * descreve o que o sistema FAZ, e está registrado como pendência em
 * docs/decisions/0005-limiares-ambientais.md. */
const FAIXA_SOLO_PCT = { min: 20, max: 80 };

/** Tensão crítica de irrigação para tomate de mesa, em kPa (Braga,
 * Feltrim e Borges, 2022, p. 105). Não entra em comparação nenhuma: o
 * sensor não mede kPa. Está aqui para o pé do cartão citar o critério. */
const TENSAO_CRITICA_KPA = { min: 15, max: 25 };

/** Fração de água disponível a manter no solo, da FAO-56 (p = 0,40 para
 * tomate, logo 1 - 0,40). Também não entra em comparação.
 *
 * A FAO-56 ainda corrige p pela evapotranspiração,
 * p = 0,40 + 0,04 (5 - ETc), limitado a 0,1 <= p <= 0,8. Numa estufa
 * quente o ETc passa de 5 mm/dia, p cai e o piso sobe acima de 60%.
 * Esse refinamento fica para depois de o ponto de murcha ser medido:
 * aplicá-lo antes seria precisão decorativa. */
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
    /** De onde o número da linha vem, o que decide o traço E o texto.
     * Existe para o olho não ler as duas origens com o mesmo peso.
     *
     * 'recomendacao' = fonte publicada, na mesma unidade que o sensor
     * mede, então a linha É a recomendação (traço curto, 4,4).
     * 'medido' = medição feita nesta estufa, na escala deste sensor.
     * Confiável para este vaso e não generalizável, diferente dos dois
     * (traço longo, 8,4).
     *
     * Havia um terceiro, 'alerta', para quando a linha marcava só onde o
     * alerta do sistema dispara, sem respaldo. Saiu em 2026-11-06, quando
     * a linha do solo passou a ser a capacidade de campo medida e nenhuma
     * série mais precisou dele. */
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
