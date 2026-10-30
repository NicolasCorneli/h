import type { CameraView } from 'expo-camera';
import { useEffect, useRef, useState, type RefObject } from 'react';
import { AppState } from 'react-native';

import { prepararFotoParaEnvio, simulacoes } from '@/services/api';
import { reduzirParaEnvio } from '@/services/imagemLocal';

/** Intervalo entre uma conferência e a próxima (depois da resposta, nunca sobrepostas). */
const INTERVALO_MS = 1200;
/** Largura da miniatura enviada: o bastante para o detector, leve para a rede. */
const LARGURA_MINIATURA = 360;

export type Enquadramento = 'procurando' | 'no_guia';

/**
 * Confere ao vivo se o rosto está dentro do guia da câmera.
 *
 * A câmera do Expo não detecta rostos no aparelho. Enquanto a tela está aberta, uma foto
 * pequena e silenciosa é tirada a cada pouco mais de um segundo e o servidor responde se
 * há um rosto de frente na região do guia. A miniatura não é guardada. Se a rede falhar,
 * a orientação volta para "enquadre o rosto": nunca se mostra uma confirmação que o
 * servidor não deu.
 */
export function useEnquadramento(
  camera: RefObject<CameraView | null>,
  clienteId: string | null,
  ativo: boolean
): Enquadramento {
  const [estado, setEstado] = useState<Enquadramento>('procurando');
  const ligado = useRef(ativo);
  ligado.current = ativo;

  useEffect(() => {
    if (!ativo || !clienteId) return;
    let cancelado = false;
    let temporizador: ReturnType<typeof setTimeout> | undefined;
    let emPrimeiroPlano = AppState.currentState === 'active';
    const assinatura = AppState.addEventListener('change', (s) => {
      emPrimeiroPlano = s === 'active';
    });

    async function conferir() {
      if (cancelado) return;
      try {
        if (emPrimeiroPlano && ligado.current && camera.current) {
          const quadro = await camera.current.takePictureAsync({ quality: 0.4, shutterSound: false });
          if (quadro && !cancelado) {
            const miniatura = await reduzirParaEnvio(
              quadro.uri,
              quadro.width,
              quadro.height,
              LARGURA_MINIATURA
            );
            const resposta = await simulacoes.conferirEnquadramento(
              clienteId!,
              await prepararFotoParaEnvio(miniatura)
            );
            if (!cancelado) setEstado(resposta.rostoNoGuia ? 'no_guia' : 'procurando');
          }
        }
      } catch {
        if (!cancelado) setEstado('procurando');
      }
      if (!cancelado) temporizador = setTimeout(() => void conferir(), INTERVALO_MS);
    }

    temporizador = setTimeout(() => void conferir(), 800);
    return () => {
      cancelado = true;
      if (temporizador) clearTimeout(temporizador);
      assinatura.remove();
    };
  }, [ativo, clienteId, camera]);

  return ativo ? estado : 'procurando';
}
