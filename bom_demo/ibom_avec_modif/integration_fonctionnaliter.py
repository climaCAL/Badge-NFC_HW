import os
import sys

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(SCRIPT_DIR, 'ibom.html')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'ibom_test.html')

# Marqueurs pour le nettoyage automatique
START_MARKER = "<!-- DEBUT DU MODULE DE TEST (Injecté par Python) -->"
END_MARKER = "<!-- FIN DU MODULE DE TEST -->"

INJECTION_CONTENT = f"""
{START_MARKER}
<style>
    /* --- STYLES MODIFIÉS --- */
    .custom-overlay {{
        display: none;
        position: fixed;
        /* La position et la taille seront définies par JS pour coller au tableau */
        z-index: 99999;
        
        /* Fond sombre pour cacher la liste ("cacher le côté gauche") */
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(4px);
        
        /* Centrage du contenu DANS la zone gauche */
        justify-content: center;
        align-items: center;
        font-family: 'Segoe UI', Verdana, sans-serif;
    }}
    
    .custom-overlay.active {{
        display: flex;
    }}

    .custom-card {{
        background: #2b3e50;
        color: #ecf0f1;
        padding: 25px;
        border-radius: 12px;
        text-align: left;
        box-shadow: 0 15px 40px rgba(0,0,0,0.8);
        width: 85%; /* Largeur relative à la zone gauche */
        max-width: 380px;
        position: relative;
        border: 1px solid #4a6fa5;
    }}

    .close-btn {{
        position: absolute;
        top: 15px;
        right: 15px;
        background: none;
        border: none;
        color: #aaa;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        line-height: 1;
    }}
    .close-btn:hover {{ color: #fff; }}

    h2 {{
        margin-top: 0;
        color: #ffb629;
        border-bottom: 1px solid #555;
        padding-bottom: 10px;
        font-size: 20px;
        margin-bottom: 20px;
    }}

    .info-row {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
        font-size: 1.1em;
    }}
    .info-label {{ font-weight: bold; color: #8fa1b3; }}
    .info-value {{ font-family: monospace; color: #fff; }}

    .action-btn {{
        width: 100%;
        padding: 15px;
        border: none;
        border-radius: 6px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        margin-top: 20px;
        transition: background 0.2s;
    }}

    .btn-next {{ background: #27ae60; color: white; }}
    .btn-next:hover {{ background: #2ecc71; }}

    .btn-submit {{ background: #e67e22; color: white; }}
    .btn-submit:hover {{ background: #d35400; }}

    textarea.rework-input {{
        width: 100%;
        height: 100px;
        background: #1a252f;
        border: 1px solid #4a6fa5;
        border-radius: 4px;
        color: white;
        padding: 10px;
        font-family: sans-serif;
        resize: none;
        box-sizing: border-box;
    }}
    textarea.rework-input:focus {{ outline: 2px solid #ffb629; }}
</style>

<!-- MODALE DÉTAILS / SUIVANT -->
<div id="details-overlay" class="custom-overlay">
    <div class="custom-card">
        <button class="close-btn" onclick="closeOverlay('details-overlay')">&times;</button>
        <h2>Montage en cours</h2>
        
        <div class="info-row">
            <span class="info-label">Référence:</span>
            <span class="info-value" id="det-ref">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Valeur:</span>
            <span class="info-value" id="det-val">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Empreinte:</span>
            <span class="info-value" id="det-fp">--</span>
        </div>

        <button id="btn-next-comp" class="action-btn btn-next">
            ✔ Fait & Suivant
        </button>
    </div>
</div>

<!-- MODALE REWORK -->
<div id="rework-overlay" class="custom-overlay">
    <div class="custom-card">
        <button class="close-btn" onclick="closeRework()">&times;</button>
        <h2 style="color: #e74c3c;">Reprise Composante</h2>
        
        <p style="margin-bottom: 10px; color: #ccc;">Raison de la reprise pour <b id="rew-ref" style="color:white">--</b> :</p>
        <textarea id="rework-reason" class="rework-input" placeholder="Ex: Soudure froide, mal aligné..."></textarea>
        
        <button id="btn-submit-rework" class="action-btn btn-submit">
            Enregistrer
        </button>
    </div>
</div>

<script>
let currentWorkRowId = null; 

function closeOverlay(id) {{
    document.getElementById(id).classList.remove('active');
}}

function closeRework() {{
    closeOverlay('rework-overlay');
    if (currentWorkRowId) {{
        const handler = window.highlightHandlers.find(h => h.id === currentWorkRowId);
        if (handler) {{
            handler.handler(); 
            smoothScrollToRow(currentWorkRowId);
        }}
    }}
}}

// Nouvelle fonction pour positionner l'overlay uniquement sur la zone BOM (gauche)
function positionOverlay(overlayId) {{
    const overlay = document.getElementById(overlayId);
    const bomDiv = document.getElementById('bomdiv'); // C'est l'élément qui contient la liste
    
    if (bomDiv && overlay) {{
        const rect = bomDiv.getBoundingClientRect();
        overlay.style.top = rect.top + 'px';
        overlay.style.left = rect.left + 'px';
        overlay.style.width = rect.width + 'px';
        overlay.style.height = rect.height + 'px';
    }}
}}

function getPlacedCheckboxName() {{
    if (window.settings && window.settings.checkboxes) {{
        const found = window.settings.checkboxes.find(c => c.toLowerCase().includes('place'));
        if(found) return found;
        else if (window.settings.checkboxes.length > 0) return window.settings.checkboxes[window.settings.checkboxes.length - 1];
    }}
    return "Placed"; 
}}

function getComponentData(index) {{
    if (!window.pcbdata || !window.pcbdata.footprints[index]) return null;
    const comp = window.pcbdata.footprints[index];
    
    let val = "N/A", fp = "N/A";
    if(window.pcbdata.bom.fields && window.pcbdata.bom.fields[index]) {{
        const fields = window.pcbdata.bom.fields[index];
        if(window.config && window.config.fields) {{
            const valIdx = window.config.fields.indexOf("Value");
            const fpIdx = window.config.fields.indexOf("Footprint");
            if(valIdx >= 0) val = fields[valIdx];
            if(fpIdx >= 0) fp = fields[fpIdx];
        }}
    }}
    return {{ ref: comp.ref, val: val, fp: fp, index: index }};
}}

document.addEventListener('DOMContentLoaded', () => {{
    
    document.getElementById('btn-next-comp').addEventListener('click', () => {{
        if (window.currentHighlightedRowId) {{
            const placedName = getPlacedCheckboxName();
            window.checkBomCheckbox(window.currentHighlightedRowId, placedName);
            window.highlightNextRow(); 

            setTimeout(() => {{
                if (window.highlightedFootprints && window.highlightedFootprints.length > 0) {{
                    const idx = window.highlightedFootprints[0];
                    const data = getComponentData(idx);
                    
                    document.getElementById('det-ref').textContent = data.ref;
                    document.getElementById('det-val').textContent = data.val;
                    document.getElementById('det-fp').textContent = data.fp;
                    currentWorkRowId = window.currentHighlightedRowId;
                }} else {{
                    closeOverlay('details-overlay');
                }}
            }}, 50);
        }}
    }});

    document.getElementById('btn-submit-rework').addEventListener('click', () => {{
        const reason = document.getElementById('rework-reason').value;
        const ref = document.getElementById('rew-ref').textContent;
        if (reason.trim() === "") {{ alert("Raison requise."); return; }}
        console.log("REWORK:", ref, reason);
        document.getElementById('rework-reason').value = "";
        closeRework();
    }});

    // --- INTERCEPTION DES CLICS (Version v5) ---
    document.body.addEventListener('click', (e) => {{
        // 1. Ignorer les clics dans nos propres cartes
        if (e.target.closest('.custom-card')) return;

        // 2. CORRECTION CRITIQUE : Ignorer si on clique sur une case à cocher (INPUT)
        // Cela permet de cocher "Placed" manuellement sans déclencher la fenêtre
        if (e.target.tagName === 'INPUT') return;

        // 3. Vérification : Clic dans le tableau uniquement
        const insideBomTable = e.target.closest('#bomtable');
        const targetRow = e.target.closest('tr');
        
        if (insideBomTable && targetRow) {{
            
            setTimeout(() => {{
                if (!window.highlightedFootprints || window.highlightedFootprints.length === 0) return;
                
                const index = window.highlightedFootprints[0];
                const rowId = window.currentHighlightedRowId;
                const data = getComponentData(index);

                // Detection "Déjà Fait"
                let isChecked = false;
                const placedName = getPlacedCheckboxName();
                if (window.settings && window.settings.checkboxStoredRefs && window.settings.checkboxStoredRefs[placedName]) {{
                    const storedArray = window.settings.checkboxStoredRefs[placedName].split(',');
                    if (storedArray.includes(String(index))) isChecked = true;
                }}
                
                // Fallback visuel
                if (!isChecked) {{
                    const rowEl = document.getElementById(rowId);
                    if (rowEl) {{
                        const checkboxes = rowEl.querySelectorAll('input[type="checkbox"]');
                        if (checkboxes.length > 0 && checkboxes[checkboxes.length - 1].checked) isChecked = true;
                    }}
                }}

                if (isChecked) {{
                    // REWORK
                    document.getElementById('rew-ref').textContent = data.ref;
                    document.getElementById('rework-reason').value = ""; 
                    
                    // On positionne et on affiche
                    positionOverlay('rework-overlay');
                    document.getElementById('rework-overlay').classList.add('active');
                    document.getElementById('details-overlay').classList.remove('active');
                }} else {{
                    // NORMAL
                    currentWorkRowId = rowId;
                    document.getElementById('det-ref').textContent = data.ref;
                    document.getElementById('det-val').textContent = data.val;
                    document.getElementById('det-fp').textContent = data.fp;
                    
                    // On positionne et on affiche
                    positionOverlay('details-overlay');
                    document.getElementById('details-overlay').classList.add('active');
                    document.getElementById('rework-overlay').classList.remove('active');
                }}

            }}, 100); 
        }}
    }});
    
    console.log("Module Production v5 (Fix checkbox + Masquage gauche uniquement).");
}});
</script>
{END_MARKER}
"""

def main():
    print("-" * 50)
    print("SCRIPT D'INJECTION FLUX PRODUCTION")
    print("-" * 50)
    print(f"Source : {{os.path.basename(SOURCE_FILE)}}")
    print(f"Sortie : {{os.path.basename(OUTPUT_FILE)}}")

    if not os.path.exists(SOURCE_FILE):
        if os.path.exists(OUTPUT_FILE):
            print(f"Info : 'ibom.html' introuvable. Utilisation de 'ibom_test.html' comme source.")
            read_path = OUTPUT_FILE
        else:
            print("[ERREUR] 'ibom.html' introuvable.")
            input("Appuyez sur Entrée...")
            return
    else:
        read_path = SOURCE_FILE

    try:
        try:
            with open(read_path, 'r', encoding='utf-8') as f: content = f.read()
        except:
            with open(read_path, 'r', encoding='latin-1') as f: content = f.read()

        if START_MARKER in content:
            print("Nettoyage ancienne version...")
            s = content.find(START_MARKER)
            e = content.find(END_MARKER) + len(END_MARKER)
            content = content[:s] + content[e:]

        idx = content.lower().rfind('</body>')
        if idx != -1:
            print("Injection du code...")
            new_content = content[:idx] + INJECTION_CONTENT + '\\n' + content[idx:]
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: f.write(new_content)
            print("[SUCCÈS] 'ibom_test.html' mis à jour !")
        else:
            print("[ERREUR] Balise </body> non trouvée.")

    except Exception as e:
        print(f"[ERREUR] {{e}}")

    input("\\nAppuyez sur Entrée pour fermer...")

if __name__ == "__main__":
    main()