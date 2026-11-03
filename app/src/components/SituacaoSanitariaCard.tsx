import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

/**
 * Distribuição dos diagnósticos recentes, por estado da planta.
 *
 * POR QUE BARRA EMPILHADA E NÃO ROSCA
 * -----------------------------------
 * Era um VictoryPie com duas fatias. Com todos os diagnósticos numa
 * categoria só, o que aconteceu em 2026-11-03, ele vira um anel sólido
 * de uma cor, que parece defeito de renderização. Uma barra cheia de
 * uma cor só parece intencional.
 *
 * A barra também permite ordem por severidade da esquerda para a
 * direita, verde para âmbar para vermelho, que se lê sem consultar
 * legenda.
 *
 * POR QUE TRÊS ESTADOS E NÃO DOIS
 * -------------------------------
 * O card contava "saudáveis" contra "com doença", sendo "com doença"
 * tudo que não fosse saudável. Quando a classe `estresse_foliar` entrou
 * em produção, o card passou a exibir "Com doença (10)" para uma planta
 * que o próprio app descreve, na tela de Diagnóstico, como "alteração na
 * folha que NÃO corresponde às doenças que o sistema reconhece".
 *
 * Estresse pede atenção, não tratamento. Chamar de doença manda o
 * produtor pulverizar uma planta que não tem doença.
 *
 * AS NÃO ANALISADAS FICAM FORA DA BARRA
 * -------------------------------------
 * Foto reprovada na guarda de qualidade não diz nada sobre a planta.
 * Colocá-la na barra misturaria "o que a planta tem" com "o que não deu
 * para ver". Ela vai numa linha abaixo, como nota.
 */

interface SituacaoSanitariaCardProps {
  saudaveis: number;
  comEstresse: number;
  comDoenca: number;
  /** Fotos que a guarda de qualidade recusou analisar. */
  semAnalise: number;
}

/** O subtítulo descreve a AMOSTRA, não uma janela de tempo.
 *
 * Ele dizia "Diagnósticos das últimas 48 horas", com 48 fixo no código,
 * enquanto a busca real era de outra janela. O número no texto e o
 * número na consulta viviam em arquivos diferentes e, na primeira vez
 * que a consulta mudou, o rótulo passou a mentir sem que nada quebrasse.
 *
 * Contar o que está no próprio card elimina a possibilidade: seja qual
 * for a janela que services/diagnosticos.ts usar amanhã, esta frase
 * continua verdadeira. */
function descreverAmostra(total: number): string {
  if (total === 0) return 'Nenhuma foto analisada ainda';
  if (total === 1) return 'Baseado na última foto analisada';
  return `Baseado nas ${total} fotos analisadas mais recentes`;
}

export function SituacaoSanitariaCard({
  saudaveis,
  comEstresse,
  comDoenca,
  semAnalise,
}: SituacaoSanitariaCardProps) {
  const total = saudaveis + comEstresse + comDoenca;

  const faixas = [
    { rotulo: 'Saudáveis', quantidade: saudaveis, cor: colors.oliveGreen },
    { rotulo: 'Com estresse', quantidade: comEstresse, cor: colors.cuidado },
    { rotulo: 'Com doença', quantidade: comDoenca, cor: colors.danger },
  ];

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Situação sanitária</Text>
      <Text style={styles.subtitulo}>{descreverAmostra(total)}</Text>

      {total === 0 ? (
        <Text style={styles.vazio}>
          Assim que a primeira foto for analisada, a distribuição aparece aqui.
        </Text>
      ) : (
        <>
          <View style={styles.barra}>
            {faixas
              .filter((f) => f.quantidade > 0)
              .map((f) => (
                <View
                  key={f.rotulo}
                  style={{
                    flex: f.quantidade,
                    backgroundColor: f.cor,
                  }}
                />
              ))}
          </View>

          <View style={styles.legenda}>
            {faixas.map((f) => (
              <View key={f.rotulo} style={styles.itemLegenda}>
                <View style={[styles.marcador, { backgroundColor: f.cor }]} />
                <Text
                  style={[
                    styles.textoLegenda,
                    f.quantidade === 0 && styles.textoLegendaZerada,
                  ]}
                >
                  {f.rotulo} ({f.quantidade})
                </Text>
              </View>
            ))}
          </View>
        </>
      )}

      {semAnalise > 0 && (
        <Text style={styles.nota}>
          {semAnalise === 1
            ? '1 foto não pôde ser analisada e ficou fora da conta.'
            : `${semAnalise} fotos não puderam ser analisadas e ficaram fora da conta.`}
        </Text>
      )}
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
    marginBottom: 14,
  },
  barra: {
    flexDirection: 'row',
    height: 22,
    borderRadius: 11,
    overflow: 'hidden',
    backgroundColor: colors.cream,
  },
  legenda: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 12,
  },
  itemLegenda: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    marginBottom: 4,
  },
  marcador: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 6,
  },
  textoLegenda: {
    fontSize: 13,
    color: colors.textDark,
  },
  textoLegendaZerada: {
    color: colors.textMuted,
  },
  vazio: {
    fontSize: 13,
    color: colors.textMuted,
  },
  nota: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 10,
    fontStyle: 'italic',
  },
});
