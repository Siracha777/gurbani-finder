from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Read transcription file
with open('output/transcribed.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Convert each line to Gurmukhi
gurmukhi_lines = []
for line in lines:
    gurmukhi_line = transliterate(line.strip(), sanscript.DEVANAGARI, sanscript.GURMUKHI)
    gurmukhi_lines.append(gurmukhi_line)

# Save the Gurmukhi transcription
with open('output/transcribed_gurmukhi.txt', 'w', encoding='utf-8') as f:
    for line in gurmukhi_lines:
        f.write(line + '\n')

print("Conversion to Gurmukhi done! Check output/transcribed_gurmukhi.txt")
