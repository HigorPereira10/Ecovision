/**
 * app/src/components/FormularioGastoModal.tsx
 *
 * Formulário de registro de gasto (categoria, valor, data), aberto via
 * botão "+ Registrar novo gasto" na tela Financeiro. Salva chamando
 * registrarGasto() do services/gastos.ts.
 */

import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { colors } from '../theme/colors';
import { CATEGORIAS_GASTO } from '../services/gastos';

interface Props {
  visivel: boolean;
  onFechar: () => void;
  onSalvar: (dados: { categoria: string; descricao: string; valor: number; data: string }) => Promise<void>;
}

export function FormularioGastoModal({ visivel, onFechar, onSalvar }: Props) {
  const [categoria, setCategoria] = useState<string>(CATEGORIAS_GASTO[0]);
  const [descricao, setDescricao] = useState('');
  const [valorTexto, setValorTexto] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const limparEFechar = () => {
    setCategoria(CATEGORIAS_GASTO[0]);
    setDescricao('');
    setValorTexto('');
    setErro(null);
    onFechar();
  };

  const handleSalvar = async () => {
    const valorNumerico = Number(valorTexto.replace(',', '.'));

    if (!descricao.trim()) {
      setErro('Informe uma descrição para o gasto.');
      return;
    }
    if (!valorNumerico || valorNumerico <= 0) {
      setErro('Informe um valor válido.');
      return;
    }

    setErro(null);
    setSalvando(true);
    try {
      await onSalvar({
        categoria,
        descricao: descricao.trim(),
        valor: valorNumerico,
        data: new Date().toISOString(),
      });
      limparEFechar();
    } catch (e) {
      setErro('Não foi possível salvar o gasto. Tente novamente.');
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Modal visible={visivel} animationType="slide" transparent onRequestClose={limparEFechar}>
      <KeyboardAvoidingView
        style={styles.overlay}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.folha}>
          <ScrollView keyboardShouldPersistTaps="handled">
            <Text style={styles.titulo}>Registrar novo gasto</Text>

            <Text style={styles.rotulo}>Categoria</Text>
            <View style={styles.chips}>
              {CATEGORIAS_GASTO.map((c) => (
                <Pressable
                  key={c}
                  onPress={() => setCategoria(c)}
                  style={[styles.chip, categoria === c && styles.chipSelecionado]}
                >
                  <Text
                    style={[
                      styles.chipTexto,
                      categoria === c && styles.chipTextoSelecionado,
                    ]}
                  >
                    {c}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.rotulo}>Descrição</Text>
            <TextInput
              style={styles.input}
              placeholder="Ex: Fertilizante NPK 20kg"
              placeholderTextColor={colors.textMuted}
              value={descricao}
              onChangeText={setDescricao}
            />

            <Text style={styles.rotulo}>Valor (R$)</Text>
            <TextInput
              style={styles.input}
              placeholder="Ex: 150,00"
              placeholderTextColor={colors.textMuted}
              keyboardType="decimal-pad"
              value={valorTexto}
              onChangeText={setValorTexto}
            />

            {erro && <Text style={styles.erro}>{erro}</Text>}

            <Pressable
              style={[styles.botaoSalvar, salvando && styles.botaoDesabilitado]}
              onPress={handleSalvar}
              disabled={salvando}
            >
              <Text style={styles.botaoSalvarTexto}>
                {salvando ? 'Salvando...' : 'Salvar gasto'}
              </Text>
            </Pressable>

            <Pressable style={styles.botaoCancelar} onPress={limparEFechar}>
              <Text style={styles.botaoCancelarTexto}>Cancelar</Text>
            </Pressable>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  folha: {
    backgroundColor: colors.cream,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '85%',
  },
  titulo: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.textDark,
    marginBottom: 16,
  },
  rotulo: {
    fontSize: 13,
    color: colors.textMuted,
    marginBottom: 6,
    marginTop: 10,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.cream,
  },
  chipSelecionado: {
    backgroundColor: colors.oliveGreen,
    borderColor: colors.oliveGreen,
  },
  chipTexto: {
    color: colors.textDark,
    fontSize: 13,
  },
  chipTextoSelecionado: {
    color: colors.white,
    fontWeight: '600',
  },
  input: {
    backgroundColor: colors.white,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    color: colors.textDark,
  },
  erro: {
    color: colors.danger,
    fontSize: 12,
    marginTop: 10,
  },
  botaoSalvar: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 20,
  },
  botaoDesabilitado: {
    opacity: 0.6,
  },
  botaoSalvarTexto: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 15,
  },
  botaoCancelar: {
    alignItems: 'center',
    paddingVertical: 12,
    marginBottom: 8,
  },
  botaoCancelarTexto: {
    color: colors.textMuted,
    fontSize: 13,
  },
});
