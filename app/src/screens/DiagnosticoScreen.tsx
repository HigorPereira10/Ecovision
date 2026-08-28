/**
 * app/src/screens/DiagnosticoScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Exibe o diagnóstico mais recente, incluindo a foto da folha. A URL
 * da imagem vem PRONTA da API (Blueprint Seção 4.2, passo 5) — esta
 * tela nunca busca a imagem diretamente no Supabase Storage.
 *
 * Versão atual usa dados mockados (src/mocks/diagnosticos.json e
 * src/mocks/imagens.json) até o endpoint da API estar definido/pronto.
 *
 * NOTA: imagens.json hoje só tem 1 registro, mas diagnosticos.json
 * tem 6 (registro_imagem_id de 1 a 6). Enquanto isso não é corrigido,
 * usamos um placeholder visual pra ids sem imagem correspondente.
 *
 * NOTA: "MobileNetV2 (TFLite)" está fixo no código porque não existe
 * campo "modelo" em diagnosticos.json ainda.
 *
 * NOTA: esta tela é raiz de aba (Tab.Navigator), não faz parte de um
 * stack empilhado — por isso não tem botão de voltar. headerShown está
 * como false na definição da aba em AppNavigator.tsx, e o header abaixo
 * (logo + título) segue o mesmo padrão do DashboardScreen.
 */

import React, { useState } from 'react';
import {
  View,
  Image,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import diagnosticosMock from '../mocks/diagnosticos.json';
import imagensMock from '../mocks/imagens.json';
import { colors } from '../theme/colors';

type Diagnostico = {
  id: number;
  registro_imagem_id: number;
  classificacao: string;
  confianca: number;
  recomendacao: string;
  timestamp: string;
};

type RegistroImagem = {
  id: number;
  dispositivo_id: number;
  caminho_arquivo: string;
  resolucao: string;
  timestamp: string;
};

const MODELO_IA = 'MobileNetV2 (TFLite)';

function normalizarTexto(texto: string): string {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function isSaudavel(classificacao: string): boolean {
  return normalizarTexto(classificacao).includes('saudavel');
}

function getRegistroImagem(id: number): RegistroImagem | undefined {
  return (imagensMock as RegistroImagem[]).find((img) => img.id === id);
}

function formatarData(timestamp: string): string {
  return new Date(timestamp).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function DiagnosticoScreen() {
  const diagnosticos = diagnosticosMock as Diagnostico[];
  const [diagnosticoAtualId, setDiagnosticoAtualId] = useState<number>(diagnosticos[0]?.id);

  const diagnostico = diagnosticos.find((d) => d.id === diagnosticoAtualId);

  if (!diagnostico) {
    return (
      <View style={styles.centro}>
        <Text style={styles.textoVazio}>Nenhum diagnóstico disponível ainda.</Text>
      </View>
    );
  }

  const registroImagem = getRegistroImagem(diagnostico.registro_imagem_id);
  const saudavel = isSaudavel(diagnostico.classificacao);
  const corStatus = saudavel ? colors.oliveGreen : colors.danger;
  const confiancaPercentual = Math.round(diagnostico.confianca * 100);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image
          source={require('../../assets/images/logo-ecovision.png')}
          style={styles.logo}
        />
        <Text style={styles.headerTitulo}>Diagnóstico de Campo</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {registroImagem ? (
          <Image source={{ uri: registroImagem.caminho_arquivo }} style={styles.imagem} />
        ) : (
          <View style={[styles.imagem, styles.imagemPlaceholder]}>
            <Text style={styles.imagemPlaceholderTexto}>Imagem não disponível</Text>
          </View>
        )}

        <View style={styles.cardClassificacao}>
          <Text style={styles.labelClassificacao}>CLASSIFICAÇÃO DA IA</Text>

          <View style={styles.linhaClassificacao}>
            <Text style={[styles.classificacaoTexto, { color: corStatus }]} numberOfLines={2}>
              {diagnostico.classificacao}
            </Text>
            <View style={[styles.badgeConfianca, { backgroundColor: corStatus }]}>
              <Text style={styles.badgeConfiancaTexto}>{confiancaPercentual}% confiança</Text>
            </View>
          </View>

          <View style={styles.barraFundo}>
            <View
              style={[
                styles.barraPreenchida,
                { width: `${confiancaPercentual}%`, backgroundColor: corStatus },
              ]}
            />
          </View>
        </View>

        <View style={styles.cardRecomendacao}>
          <Text style={styles.recomendacaoTitulo}>Recomendação de manejo</Text>
          <Text style={styles.recomendacaoTexto}>{diagnostico.recomendacao}</Text>
        </View>

        <Text style={styles.metaTexto}>
          Capturado em {formatarData(diagnostico.timestamp)} · {MODELO_IA}
        </Text>

        <Text style={styles.secaoTitulo}>Resultados recentes</Text>

        <View style={styles.grid}>
          {diagnosticos.map((item) => {
            const itemImagem = getRegistroImagem(item.registro_imagem_id);
            const itemSaudavel = isSaudavel(item.classificacao);
            const itemCor = itemSaudavel ? colors.oliveGreen : colors.danger;
            const selecionado = item.id === diagnostico.id;

            return (
              <TouchableOpacity
                key={item.id}
                style={styles.gridItem}
                onPress={() => setDiagnosticoAtualId(item.id)}
                activeOpacity={0.7}
              >
                {itemImagem ? (
                  <Image
                    source={{ uri: itemImagem.caminho_arquivo }}
                    style={[
                      styles.gridImagem,
                      selecionado && { borderColor: colors.oliveGreen, borderWidth: 2 },
                    ]}
                  />
                ) : (
                  <View
                    style={[
                      styles.gridImagem,
                      styles.gridImagemPlaceholder,
                      selecionado && { borderColor: colors.oliveGreen, borderWidth: 2 },
                    ]}
                  />
                )}
                <Text style={[styles.gridLabel, { color: itemCor }]} numberOfLines={1}>
                  {item.classificacao}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.cream,
  },
  header: {
    backgroundColor: colors.darkGreen,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 50,
    paddingBottom: 16,
  },
  logo: {
    width: 32,
    height: 32,
    resizeMode: 'contain',
  },
  headerTitulo: {
    color: colors.white,
    fontSize: 18,
    fontWeight: '700',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 12,
    paddingBottom: 32,
  },
  imagem: {
    width: '100%',
    height: 220,
    borderRadius: 16,
    backgroundColor: '#e5e5e5',
    marginTop: 12,
  },
  imagemPlaceholder: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  imagemPlaceholderTexto: {
    color: '#999',
    fontSize: 13,
  },
  cardClassificacao: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 16,
    marginTop: 12,
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  labelClassificacao: {
    fontSize: 11,
    letterSpacing: 0.5,
    color: '#999',
    fontWeight: '600',
    marginBottom: 6,
  },
  linhaClassificacao: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  classificacaoTexto: {
    fontSize: 19,
    fontWeight: '700',
    flex: 1,
    marginRight: 8,
  },
  badgeConfianca: {
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  badgeConfiancaTexto: {
    color: colors.white,
    fontSize: 12,
    fontWeight: '700',
  },
  barraFundo: {
    height: 6,
    backgroundColor: '#eee',
    borderRadius: 3,
    marginTop: 12,
    overflow: 'hidden',
  },
  barraPreenchida: {
    height: 6,
    borderRadius: 3,
  },
  cardRecomendacao: {
    backgroundColor: '#EEF3E7',
    borderRadius: 16,
    padding: 16,
    marginTop: 12,
  },
  recomendacaoTitulo: {
    fontWeight: '700',
    color: colors.darkGreen,
    marginBottom: 6,
    fontSize: 14,
  },
  recomendacaoTexto: {
    color: '#4a4a4a',
    fontSize: 13,
    lineHeight: 19,
  },
  metaTexto: {
    fontSize: 12,
    color: '#999',
    marginTop: 12,
    marginBottom: 20,
  },
  secaoTitulo: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.darkGreen,
    marginBottom: 10,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  gridItem: {
    width: '31%',
    marginBottom: 14,
  },
  gridImagem: {
    width: '100%',
    aspectRatio: 1,
    borderRadius: 10,
    backgroundColor: '#e5e5e5',
    borderColor: 'transparent',
  },
  gridImagemPlaceholder: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  gridLabel: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 4,
    textAlign: 'center',
  },
  centro: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
  },
  textoVazio: {
    fontSize: 14,
    color: '#666',
  },
});