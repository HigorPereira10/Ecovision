import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

/**
 * Distribuição dos diagnósticos recentes por estado da planta, em barra
 * empilhada ordenada por severidade (verde, âmbar, vermelho).
 *
 * São três estados: saudável, com estresse (pede atenção, não tratamento)
 * e com doença. As fotos não analisadas ficam fora da barra, em uma nota,
 * pois não dizem nada sobre a planta.
 */

interface SituacaoSanitariaCardProps {
  saudaveis: number;
  comEstresse: number;
  comDoenca: number;
  /** Fotos que a guarda de qualidade recusou analisar. */
  semAnalise: number;
}

/** O subtítulo descreve a amostra exibida, e não uma janela de tempo fixa,
 * para continuar correto se a consulta mudar. */
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
