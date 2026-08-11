const videoElement = document.getElementById('webcam');
const canvasElement = document.getElementById('output_canvas');
const ctx = canvasElement.getContext('2d');

const gameWidth = 1280;
const gameHeight = 720;

// Tamanho dos quadrados dos cantos
const boxSize = 180;

// Definição exata das posições dos 4 cantos na tela de 1280x720
const corners = {
    topLeft: { x: 40, y: 40, w: boxSize, h: boxSize, color: 'green', active: false },
    topRight: { x: gameWidth - boxSize - 40, y: 40, w: boxSize, h: boxSize, color: 'yellow', active: false },
    bottomLeft: { x: 40, y: gameHeight - boxSize - 40, w: boxSize, h: boxSize, color: 'red', active: false },
    bottomRight: { x: gameWidth - boxSize - 40, y: gameHeight - boxSize - 40, w: boxSize, h: boxSize, color: 'blue', active: false }
};

function onResults(results) {
    ctx.save();
    
    // 1. Limpa a tela e pinta o fundo do jogo
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, gameWidth, gameHeight);

    // Reseta o estado de ativação dos cantos
    for (let key in corners) {
        corners[key].active = false;
    }

    // 2. Verifica se a mão está dentro de algum dos cantos
    if (results.multiHandLandmarks) {
        for (const landmarks of results.multiHandLandmarks) {
            const indexTip = landmarks[8];
            const handX = (1 - indexTip.x) * gameWidth; 
            const handY = indexTip.y * gameHeight;

            for (let key in corners) {
                let c = corners[key];
                if (handX >= c.x && handX <= c.x + c.w && handY >= c.y && handY <= c.y + c.h) {
                    c.active = true;
                }
            }
        }
    }

    // 3. Desenhar os 4 cantos na tela perfeitamente posicionados
    for (let key in corners) {
        let c = corners[key];

        ctx.save();
        ctx.beginPath();
        ctx.rect(c.x, c.y, c.w, c.h);
        ctx.clip(); // Recorta apenas na área do canto correspondente

        // Desenha a câmera invertida no eixo X para o movimento ficar natural
        ctx.save();
        ctx.scale(-1, 1);
        ctx.drawImage(results.image, -gameWidth, 0, gameWidth, gameHeight);
        ctx.restore();

        ctx.restore(); // Sai do recorte

        // Desenha a borda do canto (muda para branco brilhante se a mão estiver em cima)
        ctx.strokeStyle = c.active ? '#FFFFFF' : c.color;
        ctx.lineWidth = c.active ? 6 : 3;
        ctx.strokeRect(c.x, c.y, c.w, c.h);
        
        // Se a mão estiver ativa no canto, preenche com a cor correspondente translúcida
        if (c.active) {
            ctx.fillStyle = c.color;
            ctx.globalAlpha = 0.4; 
            ctx.fillRect(c.x, c.y, c.w, c.h);
            ctx.globalAlpha = 1.0; 
        }
    }

    // 4. Texto central do jogo
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '28px Arial';
    ctx.fillText("Coloque a mão nos cantos!", gameWidth / 2 - 160, gameHeight / 2);

    ctx.restore();
}

const hands = new Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
});

hands.setOptions({
    maxNumHands: 2,
    modelComplexity: 1,
    minDetectionConfidence: 0.6,
    minTrackingConfidence: 0.6
});

hands.onResults(onResults);

const camera = new Camera(videoElement, {
    onFrame: async () => {
        await hands.send({image: videoElement});
    },
    width: 1280,
    height: 720
});
camera.start();