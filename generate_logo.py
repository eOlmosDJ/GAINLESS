import math

from PIL import Image, ImageDraw, ImageFont





def create_gainless_logo():

    # Renderizamos a 1024x1024 (Supersampling 4x) para bordes perfectamente suaves

    size = 1024

    cx, cy = size / 2, size / 2

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)



    # 1. Base de chasis negro anodizado con esquinas redondeadas y bisel metálico oscuro

    pad = 24

    draw.rounded_rectangle(

        [pad, pad, size - pad, size - pad],

        radius=210, fill=(10, 11, 14, 255), outline=(45, 49, 58, 255), width=14

    )

    draw.rounded_rectangle(

        [pad + 18, pad + 18, size - pad - 18, size - pad - 18],

        radius=192, fill=(14, 15, 19, 255), outline=(26, 28, 34, 255), width=6

    )



    # 2. Puntitos blancos exteriores de escala de ganancia (sector izquierdo/superior)

    r_dots = 405

    dot_angles = [45, 72, 99, 126, 153, 180, 207, 234, 261, 288, 315]

    for ang_deg in dot_angles:

        rad = math.radians(ang_deg)

        dx = cx + r_dots * math.cos(rad)

        dy = cy - r_dots * math.sin(rad)

        r_d = 12 if ang_deg in (99, 180, 261) else 9

        draw.ellipse([dx - r_d, dy - r_d, dx + r_d, dy + r_d], fill=(210, 216, 226, 255))



    # 3. Arco exterior blanco formando el cuerpo de la letra "G"

    # En PIL los ángulos van en sentido horario (0° = 3 en punto, 90° = 6 en punto, 180° = 9 en punto, 270° = 12 en punto)

    r_g_outer = 352

    r_g_inner = 296

    bbox_g_out = [cx - r_g_outer, cy - r_g_outer, cx + r_g_outer, cy + r_g_outer]

    # Arco de la G desde 22° (abajo a la derecha) pasando por abajo, izquierda y arriba hasta 318° (arriba a la derecha)

    draw.arc(bbox_g_out, start=20, end=318, fill=(242, 245, 250, 255), width=54)



    # Columna vertical derecha de la "G" (baja desde 0° hasta empalmar con el arco en 24°)

    spur_x1 = cx + r_g_inner - 2

    spur_x2 = cx + r_g_outer - 1

    draw.rounded_rectangle(

        [spur_x1, cy - 26, spur_x2, cy + 135],

        radius=14, fill=(242, 245, 250, 255)

    )



    # 4. Sombra profunda y base negra del potenciómetro gris (TRIM)

    r_black_well = 268

    draw.ellipse(

        [cx - r_black_well, cy - r_black_well, cx + r_black_well, cy + r_black_well],

        fill=(5, 6, 8, 255), outline=(28, 30, 36, 255), width=6

    )



    # Aro base gris oscuro del knob

    r_base_grey = 248

    draw.ellipse(

        [cx - r_base_grey, cy - r_base_grey, cx + r_base_grey, cy + r_base_grey],

        fill=(64, 67, 74, 255), outline=(44, 46, 52, 255), width=6

    )



    # Lateral cónico inclinado gris medio

    r_skirt = 212

    draw.ellipse(

        [cx - r_skirt, cy - r_skirt, cx + r_skirt, cy + r_skirt],

        fill=(88, 92, 100, 255), outline=(112, 117, 128, 255), width=8

    )



    # 5. Rueda superior dentada (10 muescas de agarre) del knob gris

    r_teeth = 182

    poly_points = []

    num_teeth = 10

    steps_poly = 360

    for s in range(steps_poly):

        theta = (2 * math.pi * s) / steps_poly

        r_mod = r_teeth + 14.0 * math.cos(num_teeth * theta)

        px = cx + r_mod * math.cos(theta)

        py = cy - r_mod * math.sin(theta)

        poly_points.append((px, py))



    draw.polygon(poly_points, fill=(108, 113, 122, 255), outline=(142, 148, 158, 255))



    # Cara superior interna del knob gris

    r_cap = 146

    draw.ellipse(

        [cx - r_cap, cy - r_cap, cx + r_cap, cy + r_cap],

        fill=(122, 127, 136, 255), outline=(148, 154, 164, 255), width=5

    )



    # 6. Tira blanca indicadora del knob en posición horizontal (0°)

    # Cumple doble función: es el indicador del potenciómetro y el travesaño horizontal de la "G"

    bar_h = 26

    draw.rounded_rectangle(

        [cx - 18, cy - bar_h - 6, cx + r_g_outer - 2, cy + bar_h + 6],

        radius=28, fill=(52, 55, 62, 255)

    )

    draw.rounded_rectangle(

        [cx - 10, cy - bar_h, cx + r_g_outer - 4, cy + bar_h],

        radius=24, fill=(255, 255, 255, 255)

    )



    # 7. Indicador verde-lima y etiqueta "0dB" justo donde apunta la línea horizontal de la G

    # Punto luminoso de 0dB en el extremo derecho

    led_x = cx + r_g_outer + 52

    draw.rounded_rectangle(

        [cx + r_g_outer + 14, cy - 22, cx + r_g_outer + 42, cy + 22],

        radius=10, fill=(203, 230, 0, 255)

    )



    # Etiqueta "0dB" nítida grabada en la ventana superior derecha (la abertura de la G)

    try:

        font_0db = ImageFont.truetype("arialbd.ttf", 86)

    except Exception:

        font_0db = ImageFont.load_default()



    draw.text(

        (cx + 245, cy - 118), "0dB",

        fill=(203, 230, 0, 255), anchor="mm", font=font_0db

    )



    # Guardamos PNG de alta resolución y archivo .ICO multi-tamaño para Windows

    img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)

    img_512.save("gainless_logo.png", format="PNG")



    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

    img.save("gainless.ico", format="ICO", sizes=icon_sizes)

    print("Logo generado con éxito: gainless.ico y gainless_logo.png")





if __name__ == "__main__":

    create_gainless_logo()
