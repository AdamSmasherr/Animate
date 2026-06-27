import os

f = r'D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318\AMP_AniMatePro\anim_curves\anim_curves.py'
with open(f, 'r', encoding='utf-8') as file:
    lines = file.readlines()

for i in range(len(lines)):
    if 'in locals()' in lines[i]:
        if i < 300: # line 244
            lines[i] = lines[i].replace("armature if 'armature' in locals() else obj", 'armature')
        else:
            lines[i] = lines[i].replace("armature if 'armature' in locals() else obj", 'obj')

with open(f, 'w', encoding='utf-8') as file:
    file.writelines(lines)
