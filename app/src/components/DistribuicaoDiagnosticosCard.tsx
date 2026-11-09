import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import { corDoDiagnostico } from '../theme/coresDiagnostico';
import { Diagnostico } from '../services/diagnosticos';
import { rotuloDaClasse } from '../domain/doencas';

/**
 * Distribuição dos diagnósticos no período e no campo escolhidos nos
 * filtros da tela de Histórico, com uma barra por classe e a contagem ao
 * lado. A cor segue o estado (verde para sadia, âmbar para estresse,
 * vermelho para doença, cinza para sem análise), como nas demais telas.
 */

interface DistribuicaoDiagnosticosCardProps {
  /** Já filtrados por período e por campo pela tela. */
  diagnosticos: Diagnostico[];
  /** Rótulo do período escolhido ('Últimas 48 horas'), para o cartão
   * dizer sobre o que ele está falando. */
  rotuloPeriodo: string;
  /** Rótulo do campo escolhido, ou undefined para todos. */
  rotuloCampo?: string;
}

interface Fatia {
  classe: string;
  rotulo: string;
  quantidade: number;
  cor: string;
}

/** Ordem de leitura: do mais grave para o menos, com "sem análise" por
 * último porque não é resultado sobre a planta. */
function pesoDaOrdem(d: Fatia, haviaSemDiagnostico: Set<string>): number {
  if (haviaSemDiagnostico.has(d.classe)) return 4;
  if (d.cor === colors.danger) return 0;
  if (d.cor === colors.cuidado) return 1;
  if (d.cor === colors.oliveGreen) return 2;
  return 3;
}

export function DistribuicaoDiagnosticosCard({
  diagnosticos,
  rotuloPeriodo,
  rotuloCampo,
}: DistribuicaoDiagnosticosCardProps) {
  const total = diagnosticos.length;

  const semDiagnosticoClasses = new Set(
    diagnosticos.filter((d) => d.semDiagnostico).map((d) => d.classe),
  );

  // Agrupa por classe técnica, não pelo rótulo exibido: o rótulo pode
  // repetir ou mudar de texto, a classe é a chave estável que o banco
  // guarda (diagnosticos.classe_prevista).
  const porClasse = new Map<string, Fatia>();
  for (const d of diagnosticos) {
    const existente = porClasse.get(d.classe);
    if (existente !== undefined) {
      existente.quantidade += 1;
      continue;
    }
    porClasse.set(d.classe, {
      classe: d.classe,
      rotulo: rotuloDaClasse(d.classe),
      quantidade: 1,
      // Todas as doenças usam vermelho: a cor indica a necessidade de
      // agir, e o nome da classe vem escrito ao lado.
      cor: corDoDiagnostico(d),
    });
  }

  const fatias = Array.from(porClasse.values()).sort((a, b) => {
    const ordem =
      pesoDaOrdem(a, semDiagnosticoClasses) - pesoDaOrdem(b, semDiagnosticoClasses);
    if (ordem !== 0) return ordem;
    return b.quantidade - a.quantidade;
  });

  // As barras são proporcionais à classe mais frequente, e não ao total,
  // para continuarem legíveis quando uma classe domina.
  const maiorQuantidade = fatias.reduce((m, f) => Math.max(m, f.quantidade), 0);

  const descricaoFiltro =
    rotuloCampo === undefined
      ? rotuloPeriodo
      : `${rotuloPeriodo} · ${rotuloCampo}`;

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Distribuição dos diagnósticos</Text>
      <Text style={styles.subtitulo}>
        {total === 0
          ? descricaoFiltro
          : `${descricaoFiltro} · ${total} ${total === 1 ? 'registro' : 'registros'}`}
      </Text>

      {total === 0 ? (
        <Text style={styles.vazio}>
          Nenhum diagnóstico no período selecionado. Tente ampliar o período ou
          trocar o campo.
        </Text>
      ) : (
        fatias.map((f) => {
          const porcentagem = (f.quantidade / total) * 100;
          return (
            <View key={f.classe} style={styles.linha}>
              <View style={styles.linhaCabecalho}>
                <Text style={styles.linhaRotulo} numberOfLines={1}>
                  {f.rotulo}
                </Text>
                <Text style={styles.linhaValor}>
                  {f.quantidade} ({porcentagem.toFixed(0)}%)
                </Text>
              </View>
              <View style={styles.trilha}>
                <View
                  style={[
                    styles.preenchimento,
                    {
                      // Mínimo de 2% para a classe de 1 registro em 90
                      // continuar visível como barra, e não como traço.
                      width: `${Math.max((f.quantidade / maiorQuantidade) * 100, 2)}%`,
                      backgroundColor: f.cor,
                    },
                  ]}
                />
              </View>
            </View>
          );
        })
      )}

      {semDiagnosticoClasses.size > 0 && (
        <Text style={styles.nota}>
          As porcentagens são sobre o total de fotos do período, incluindo as que
          não puderam ser analisadas.
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
  linha: {
    marginBottom: 10,
  },
  linhaCabecalho: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  linhaRotulo: {
    fontSize: 13,
    color: colors.textDark,
    flex: 1,
    marginRight: 8,
  },
  linhaValor: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textDark,
  },
  trilha: {
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.cream,
    overflow: 'hidden',
  },
  preenchimento: {
    height: 10,
    borderRadius: 5,
  },
  vazio: {
    fontSize: 13,
    color: colors.textMuted,
  },
  nota: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 4,
    fontStyle: 'italic',
  },
});
