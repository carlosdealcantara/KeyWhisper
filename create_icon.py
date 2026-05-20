from PIL import Image, ImageDraw

def create_app_icon():
    # Tamanho grande para garantir qualidade do .ico
    width = 256
    height = 256
    
    # Fundo transparente RGBA
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Cores premium (azul do microfone ativo)
    state_color = '#2563eb'
    border_color = '#3b82f6'
    
    # Círculo externo
    # Mantendo proporção: 6,6 a 58,58 num canvas 64x64.
    # Em 256x256, multiplicamos por 4:
    # 24, 24 a 232, 232
    dc.ellipse((24, 24, 232, 232), fill=state_color, outline=border_color, width=16)
    
    # Carrega fonte em negrito para o logotipo KW
    from PIL import ImageFont
    font = None
    for fn in ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "trebucbd.ttf", "tahomabd.ttf"]:
        try:
            # Tamanho da fonte grande o suficiente para aproveitar o espaço interno do círculo (~192px)
            font = ImageFont.truetype(fn, 115)
            break
        except Exception:
            continue
            
    if not font:
        font = ImageFont.load_default()
        
    # Desenha "KW" centralizado no meio do círculo (centro em 128, 128)
    dc.text((128, 128), "KW", fill='#ffffff', font=font, anchor='mm')
    
    # Salva o arquivo como .ico em formato BMP puro para compatibilidade nativa com o Windows PE Header
    image.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)], bitmap_format='bmp')
    print("Ícone icon.ico gerado com sucesso!")

if __name__ == "__main__":
    create_app_icon()
