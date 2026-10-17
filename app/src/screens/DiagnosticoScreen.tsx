/**
 * app/src/screens/DiagnosticoScreen.tsx
 *
 * Framework: Expo (React Native), decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Exibe o diagnóstico mais recente da IA, com a foto da folha que foi
 * classificada. A URL da imagem vem PRONTA da API (signed URL de bucket
 * privado): esta tela nunca fala com o Supabase Storage diretamente.
 *
 * DADO REAL desde 2026-10-11: consome services/diagnosticos.ts, que
 * chama GET /diagnosticos. Antes, os JSONs de src/mocks/ faziam a tela
 * mostrar seis folhas inventadas, com nomes de doenças que o modelo em
 * produção nem reconhece. Com o Pi ainda sem captura ligada, o normal
 * é esta tela aparecer VAZIA, e isso é o comportamento correto: vazio
 * diz a verdade, mock não.
 *
 * O rótulo da doença não vem pronto da API. A API devolve o nome
 * técnico da classe ('pinta_preta') e src/domain/doencas.ts traduz para
 * o texto da tela. É lá também que está a lista do que o modelo
 * reconhece hoje, resumida no pé desta tela para deixar o limite da IA
 * explícito ao produtor, em vez de dar a entender que ela identifica
 * qualquer doença de tomate.
 *
 * NOTA: "MobileNetV2 (TFLite)" está fixo no código porque a tabela
 * `diagnosticos` não guarda qual modelo gerou cada predição. Enquanto
 * houver um único modelo em produção isso é verdade; quando houver
 * versionamento de modelo, o campo precisa vir do banco.
 *
 * NOTA: esta tela é raiz de aba (Tab.Navigator), não faz parte de um
 * stack empilhado, por isso não tem botão de voltar. headerShown está
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
  RefreshControl,
} from 'react-native';
import { getDiagnosticosRecentes } from '../services/diagnosticos';
import { resumoDoEscopoDoModelo } from '../domain/doencas';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { EstadoVazio } from '../components/EstadoVazio';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { colors } from '../theme/colors';

const MODELO_IA = 'MobileNetV2 (TFLite)';

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
  const { dados: diagnosticos, carregando, atualizando, erro, recarregar, atualizar } =
    useCarregamentoAssincrono(getDiagnosticosRecentes, []);

  const [diagnosticoAtualId, setDiagnosticoAtualId] = useState<number | null>(null);

  if (carregando && !diagnosticos) {
    return <EstadoCarregamento />;
  }

  if (erro && !diagnosticos) {
    return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  }

  // Cabeçalho repetido no estado vazio de propósito: sem ele a tela
  // perde a identidade visual justamente no caso mais comum hoje, com o
  // Pi ainda sem captura ligada.
  const cabecalho = (
    <View style={styles.header}>
      <Image
        source={require('../../assets/images/logo-ecovision.png')}
        style={styles.logo}
      />
      <Text style={styles.headerTitulo}>Diagnóstico de Campo</Text>
      <View style={{ width: 32 }} />
    </View>
  );

  if (!diagnosticos || diagnosticos.length === 0) {
    return (
      <View style={styles.container}>
        {cabecalho}
        <EstadoVazio
          icone="scan-outline"
          titulo="Nenhum diagnóstico ainda"
          subtitulo="Quando o dispositivo enviar a primeira foto da estufa, o resultado da análise aparece aqui."
        />
      </View>
    );
  }

  const idSelecionado = diagnosticoAtualId ?? diagnosticos[0].id;
  const diagnostico = diagnosticos.find((d) => d.id === idSelecionado) ?? diagnosticos[0];
  const corStatus = diagnostico.semDiagnostico
    ? colors.textMuted
    : diagnostico.saudavel
      ? colors.oliveGreen
      : colors.danger;
  const confiancaPercentual = Math.round(diagnostico.confianca * 100);

  return (
    <View style={styles.container}>
      {cabecalho}

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={atualizando} onRefresh={atualizar} colors={[colors.oliveGreen]} />
        }
      >
        {erro && <AvisoErroInline mensagem={erro} aoTentarNovamente={atualizar} />}

        {diagnostico.urlImagem ? (
          <Image source={{ uri: diagnostico.urlImagem }} style={styles.imagem} />
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
            {/* Sem diagnóstico não há confiança a exibir: "0% confiança"
                daria a entender que houve análise e ela deu quase zero,
                quando na verdade análise nenhuma foi feita. */}
            {!diagnostico.semDiagnostico && (
              <View style={[styles.badgeConfianca, { backgroundColor: corStatus }]}>
                <Text style={styles.badgeConfiancaTexto}>{confiancaPercentual}% confiança</Text>
              </View>
            )}
          </View>

          {!diagnostico.semDiagnostico && (
            <View style={styles.barraFundo}>
              <View
                style={[
                  styles.barraPreenchida,
                  { width: `${confiancaPercentual}%`, backgroundColor: corStatus },
                ]}
              />
            </View>
          )}
        </View>

        {/* Planta sadia não tem recomendação de manejo no catálogo
            agronômico (ADR 0006), então `recomendacao` chega nula. Sem
            esta guarda o card apareceria vazio, dando a impressão de
            que o texto não carregou. */}
        {diagnostico.recomendacao && (
          <View
            style={[
              styles.cardRecomendacao,
              diagnostico.semDiagnostico && styles.cardAviso,
            ]}
          >
            <Text style={styles.recomendacaoTitulo}>
              {diagnostico.semDiagnostico
                ? 'Por que esta foto não foi analisada'
                : 'Recomendação de manejo'}
            </Text>
            <Text style={styles.recomendacaoTexto}>{diagnostico.recomendacao}</Text>
            {diagnostico.semDiagnostico && (
              <Text style={[styles.recomendacaoTexto, styles.recomendacaoSegundoParagrafo]}>
                A foto acima é a que o dispositivo capturou. Compare com o que
                você esperava ver para identificar o problema.
              </Text>
            )}
          </View>
        )}

        <Text style={styles.metaTexto}>
          Capturado em {formatarData(diagnostico.timestamp)} · {MODELO_IA}
        </Text>

        {diagnosticos.length > 1 && (
          <>
            <Text style={styles.secaoTitulo}>Resultados recentes</Text>

            <View style={styles.grid}>
              {diagnosticos.map((item) => {
                const itemCor = item.saudavel ? colors.oliveGreen : colors.danger;
                const selecionado = item.id === diagnostico.id;

                return (
                  <TouchableOpacity
                    key={item.id}
                    style={styles.gridItem}
                    onPress={() => setDiagnosticoAtualId(item.id)}
                    activeOpacity={0.7}
                  >
                    {item.urlImagem ? (
                      <Image
                        source={{ uri: item.urlImagem }}
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
          </>
        )}

        {/* O limite do modelo, dito ao produtor. Sem isto, uma folha
            com requeima classificada como "saudável" parece erro da IA,
            quando na verdade é doença que ela nunca aprendeu a ver. */}
        <Text style={styles.escopoTexto}>{resumoDoEscopoDoModelo()}</Text>
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
  // Bege de aviso, para o bloco de "nao foi analisada" nao sair verde
  // como se fosse recomendacao agronomica.
  cardAviso: { backgroundColor: '#F5EFE0' },
  recomendacaoSegundoParagrafo: { marginTop: 10 },
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
  escopoTexto: {
    fontSize: 11,
    color: '#999',
    lineHeight: 16,
    marginTop: 8,
    textAlign: 'center',
  },
});