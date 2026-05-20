import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import math
import os

def draw_premium_icons():
    # 1. Classic Microphone
    img_mic = Image.new('RGBA', (128, 128), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img_mic)
    cx, cy = 64, 64
    
    # Capsule
    # width = 28, height = 52. Center is 64, 54
    draw.rounded_rectangle((50, 28, 78, 80), radius=14, fill='white')
    
    # U-Stand Arc
    # Arc bounding box center should be 64, 70, radius = 32
    # So bbox is (32, 38, 96, 102)
    draw.arc((34, 40, 94, 100), start=0, end=180, fill='white', width=8)
    
    # U-Stand Vertical Lines
    draw.line((34, 50, 34, 70), fill='white', width=8)
    draw.line((94, 50, 94, 70), fill='white', width=8)
    
    # Base Stand Vertical
    draw.line((64, 100, 64, 116), fill='white', width=8)
    # Base Stand Horizontal
    draw.line((46, 116, 82, 116), fill='white', width=8)
    
    img_mic.save('mic_classic.png')

    # 2. Elegant Gear
    img_gear = Image.new('RGBA', (128, 128), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img_gear)
    
    # Ring
    draw.ellipse((40, 40, 88, 88), outline='white', width=8)
    # Inner hole (transparent) -> just the background
    # Teeth
    for i in range(8):
        a = math.radians(i * 45)
        x1 = cx + math.cos(a) * 20
        y1 = cy + math.sin(a) * 20
        x2 = cx + math.cos(a) * 44
        y2 = cy + math.sin(a) * 44
        draw.line((x1, y1, x2, y2), fill='white', width=8)
    
    # Draw ring again to cover lines going too far inside
    draw.ellipse((40, 40, 88, 88), outline='white', width=8)
    # Actually, we can draw a black circle inside to punch the hole
    draw.ellipse((48, 48, 80, 80), fill='black')
    
    img_gear.save('gear_elegant.png')

    # 3. Elegant Help
    img_help = Image.new('RGBA', (128, 128), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img_help)
    draw.ellipse((16, 16, 112, 112), outline='white', width=6)
    
    try:
        font = ImageFont.truetype("segoeui.ttf", 72)
    except:
        font = ImageFont.truetype("arial.ttf", 72)
    draw.text((64, 61), "?", fill='white', font=font, anchor='mm')
    
    img_help.save('help_elegant.png')

draw_premium_icons()
print("Icons generated!")
