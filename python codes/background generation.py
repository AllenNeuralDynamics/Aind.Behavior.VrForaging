# -*- coding: utf-8 -*-
"""
Created on Mon Jun 26 13:58:36 2023

@author: tiffany.ona
"""

import random
from PIL import Image, ImageDraw
import math 

save_path = 'C:/Users/tiffany.ona/OneDrive - Allen Institute/Documents/VR foraging/aind-vr-foraging/src/Textures/'

# Set the dimensions of the image and segments
image_width = 500
image_height = 500
segment_size = 100
spacing = 0

# Calculate the number of segments and the size of each segment
num_segments_x = image_width // segment_size
num_segments_y = image_height // segment_size
segment_width = segment_size
segment_height = segment_size

# Calculate the total size of each segment including spacing
segment_total_width = segment_width + spacing
segment_total_height = segment_height + spacing

# Calculate the size of the entire image including spacing
total_width = segment_total_width * num_segments_x - spacing
total_height = segment_total_height * num_segments_y - spacing

# Generate random triangles in each segment with spacing between segments
num_segments = num_segments_x * num_segments_y
min_triangle_area = 30  # Minimum area for each triangle

def calculate_triangle_area(vertices):
    """
    Calculates the area of a triangle given its vertices using Shoelace formula.
    
    Arguments:
    - vertices: A tuple or list containing the (x, y) coordinates of the triangle's vertices in the format (x1, y1, x2, y2, x3, y3).
    
    Output:
    - The area of the triangle as a floating-point number.
    """
    x1, y1, x2, y2, x3, y3 = vertices
    return abs((x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2)

def generate_random_triangle_within_segment(segment_x, segment_y):
    """
    Generates a random triangle within a segment with a minimum area.
    
    Arguments:
    - segment_x: The index of the segment along the x-axis.
    - segment_y: The index of the segment along the y-axis.
    
    Output:
    - None (The function draws the generated triangle directly on the image).
    """
    segment_left = segment_x * segment_total_width
    segment_top = segment_y * segment_total_height

    while True:
        # Generate random vertices within the segment
        x1 = random.randint(segment_left, segment_left + segment_width)
        y1 = random.randint(segment_top, segment_top + segment_height)
        x2 = random.randint(segment_left, segment_left + segment_width)
        y2 = random.randint(segment_top, segment_top + segment_height)
        x3 = random.randint(segment_left, segment_left + segment_width)
        y3 = random.randint(segment_top, segment_top + segment_height)

        # Calculate the area of the triangle
        triangle_area = calculate_triangle_area((x1, y1, x2, y2, x3, y3))

        # Check if the triangle meets the minimum area requirement
        if triangle_area >= min_triangle_area:
            break

    draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=triangle_color)
    
name = "wall.jpg"

background_color = (0, 100,0)  # RGB values for dark green
triangle_color = (255, 255, 0)  # RGB values for yellow

# background_color = (0, 0,255)  # RGB values for blue
# triangle_color = (0, 0, 255)  # RGB values for blue

# Create a new image with a grey background
image = Image.new("RGB", (total_width, total_height), background_color)
draw = ImageDraw.Draw(image)

# Generate non-overlapping triangles within each segment with spacing between segments
for segment_x in range(num_segments_x):
    for segment_y in range(num_segments_y):
        generate_random_triangle_within_segment(segment_x, segment_y)

# Save the image to a file
image.save(save_path + name, quality=10000)

def generate_different_size_rhomboids(image, section_x, section_y, section_size, rhomboid_color):
    """
    Generates rhomboids of different sizes within a section of the image.
    
    Arguments:
    - image: The PIL Image object to draw the rhomboids on.
    - section_x: The index of the section along the x-axis.
    - section_y: The index of the section along the y-axis.
    - section_size: The size of each section.
    
    Output:
    - None (The function draws the generated rhomboids directly on the image).
    """
    draw = ImageDraw.Draw(image)
    
    section_left = section_x * section_size
    section_top = section_y * section_size

    # Generate random size for the rhomboid
    rhomboid_width = random.randint(section_size // 1.5, section_size)
    rhomboid_height = random.randint(section_size // 1.5, section_size)

    # Generate random angle for the rhomboid
    angle = random.randint(0, 89)
    angle_radians = math.radians(angle)
    
    
    x1 = section_left + section_size // 2
    y1 = section_top + int(rhomboid_height / 2 * math.sin(angle_radians))
    x2 = section_left + int(rhomboid_width / 2 * math.cos(angle_radians))
    y2 = section_top + section_size // 2
    x3 = section_left + section_size // 2
    y3 = section_top + section_size - int(rhomboid_height / 2 * math.sin(angle_radians))
    x4 = section_left + section_size - int(rhomboid_width / 2 * math.cos(angle_radians))
    y4 = section_top + section_size // 2

    # Draw the rhomboid on the image
    draw.polygon([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], fill=rhomboid_color)


name = "floor.jpg"

background_color = (165, 42,42)  # RGB values for brown
rhomboid_color = (173, 216, 230)  # RGB values for light blue

# background_color = (0, 0,0)  # RGB values for black
# rhomboid_color = (0, 0, 0)  # RGB values for black

image = Image.new("RGB", (total_width, total_height), background_color)
draw = ImageDraw.Draw(image)

# Generate non-overlapping triangles within each segment with spacing between segments
for segment_x in range(num_segments_x):
    for segment_y in range(num_segments_y):
        generate_different_size_rhomboids(image, segment_x, segment_y, segment_size, rhomboid_color)

image.save(save_path+name, quality=10000)

