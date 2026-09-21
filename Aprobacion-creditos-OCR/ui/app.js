// Configuration
const API_BASE_URL       = '/api/loan';
const PERSONAS_BASE_URL  = '/api/personas';

// Global state
let lastExtractionResult  = null;
let currentPersonaId      = null;
let currentPayslipTexts   = [];    // array of 3 payslip strings (oldest → newest)

document.addEventListener('DOMContentLoaded', () => {

    const resultsSection   = document.getElementById('results-section');
    const rawJson          = document.getElementById('raw-json');
    const toggleJsonBtn    = document.getElementById('toggle-json');
    const copyResultsBtn   = document.getElementById('copy-results');
    const downloadJsonBtn  = document.getElementById('download-json-btn');
    const loadingOverlay   = document.getElementById('loading-overlay');
    const loadingText      = document.getElementById('loading-text');
    const loadingDetail    = document.getElementById('loading-detail');
    const loadingSteps     = document.getElementById('loading-steps');
    const personaDetailSec = document.getElementById('persona-detail-section');
    const decisionPanel    = document.getElementById('decision-panel');

    // ─── Bootstrap ───────────────────────────────────────────────
    loadPersonas();
    initEventListeners();

    // ─── Event Listeners ─────────────────────────────────────────
    function initEventListeners() {
        if (toggleJsonBtn && rawJson) {
            toggleJsonBtn.addEventListener('change', () => {
                rawJson.style.display = toggleJsonBtn.checked ? 'block' : 'none';
            });
        }
        if (copyResultsBtn) {
            copyResultsBtn.addEventListener('click', copyResultsToClipboard);
        }
        if (downloadJsonBtn) {
            downloadJsonBtn.addEventListener('click', downloadJson);
        }

        document.getElementById('back-to-list-btn').addEventListener('click', backToList);
        document.getElementById('analyze-persona-btn').addEventListener('click', handleAnalyzePersona);

        document.getElementById('btn-aprobar').addEventListener('click',  () => handleDecision('aprobar'));
        document.getElementById('btn-esperar').addEventListener('click',  () => handleDecision('esperar'));
        document.getElementById('btn-rechazar').addEventListener('click', () => handleDecision('rechazar'));
    }

    // ─── Load personas list ───────────────────────────────────────
    async function loadPersonas() {
        try {
            const res = await fetch(PERSONAS_BASE_URL);
            if (!res.ok) throw new Error('No se pudieron cargar los solicitantes.');
            const personas = await res.json();
            renderPersonaCards(personas);
        } catch (err) {
            document.getElementById('personas-grid').innerHTML =
                `<p style="color:#b91c1c;padding:16px 0;">${escHtml(err.message)}</p>`;
        }
    }

    // ─── Render persona cards ─────────────────────────────────────
    function renderPersonaCards(personas) {
        const grid  = document.getElementById('personas-grid');
        const badge = document.getElementById('personas-count-badge');
        badge.textContent = `${personas.length} solicitante${personas.length !== 1 ? 's' : ''}`;

        if (!personas.length) {
            grid.innerHTML = '<p style="color:#57606a;padding:1rem 0;">Sin solicitantes disponibles.</p>';
            return;
        }

        grid.innerHTML = '';
        personas.forEach(p => {
            const scoreClass = p.score_bcra >= 900 ? 'score-verde'
                             : p.score_bcra >= 750 ? 'score-amarillo'
                             : 'score-rojo';

            const card = document.createElement('div');
            card.className  = 'persona-card';
            card.dataset.id = p.id;
            card.innerHTML  = `
                <div class="persona-card-avatar">${initials(p.nombre_completo)}</div>
                <div class="persona-card-name">${escHtml(p.nombre_completo)}</div>
                <div class="persona-card-meta">DNI ${escHtml(p.dni)}<br>${escHtml(p.ciudad)}</div>
                <div class="persona-card-badges">
                    <span class="persona-card-situacion">${escHtml(p.situacion_bcra)}</span>
                    <span class="persona-card-score ${scoreClass}">Score ${p.score_bcra}</span>
                </div>
                <div class="persona-card-arrow">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
                </div>
            `;
            card.addEventListener('click', () => handlePersonaSelect(p.id));
            grid.appendChild(card);
        });
    }

    // ─── Select a persona → show detail panel ────────────────────
    async function handlePersonaSelect(personaId) {
        currentPersonaId = personaId;

        // Highlight selected card
        document.querySelectorAll('.persona-card').forEach(c => {
            c.classList.toggle('selected', Number(c.dataset.id) === personaId);
        });

        // Show loading briefly
        showLoading('Cargando perfil…', 'Generando documentos del solicitante');

        try {
            // Fetch persona profile via analyze endpoint but just get the profile
            // We use a dedicated lightweight GET for the profile preview
            const res = await fetch(`${PERSONAS_BASE_URL}/${personaId}/profile`);
            if (!res.ok) throw new Error('No se pudo cargar el perfil.');
            const profile = await res.json();
            renderPersonaDetail(profile);
        } catch (err) {
            // fallback: show detail section anyway — analyze button will fill in
            renderPersonaDetailFallback(personaId);
        } finally {
            hideLoading();
        }
    }

    function renderPersonaDetailFallback(personaId) {
        document.getElementById('persona-detail-name').textContent = `Solicitante #${personaId + 1}`;
        document.getElementById('renaper-table').innerHTML    = '<p class="no-data">Disponible al analizar.</p>';
        document.getElementById('bcra-table').innerHTML       = '<p class="no-data">Disponible al analizar.</p>';
        document.getElementById('afip-table').innerHTML       = '<p class="no-data">Disponible al analizar.</p>';
        document.getElementById('propiedad-table').innerHTML  = '<p class="no-data">Disponible al analizar.</p>';
        document.getElementById('payslip-preview').textContent = 'Los recibos se generarán al analizar.';
        showPersonaDetail();
    }

    function renderPersonaDetail(profile) {
        const r = profile.renaper;
        document.getElementById('persona-detail-name').textContent = r.nombre_completo;

        // RENAPER
        renderSimpleTable('renaper-table', [
            ['Nombre Completo', r.nombre_completo],
            ['DNI',             r.dni],
            ['CUIL',            r.cuil],
            ['Fecha Nacimiento', r.fecha_nacimiento],
            ['Domicilio',       r.domicilio],
        ]);

        // BCRA
        const b = profile.bcra;
        renderSimpleTable('bcra-table', [
            ['Situación',           b.situacion],
            ['Score Crediticio',    b.score],
            ['Deudas Activas',      b.deudas_activas_pesos > 0 ? `$ ${Number(b.deudas_activas_pesos).toLocaleString('es-AR')}` : 'Sin deudas'],
            ['Informes Negativos 12m', b.informes_negativos_12m ? '⚠ Sí' : '✓ No'],
        ]);

        // AFIP
        const a = profile.afip;
        const afipRows = [
            ['Categoría', a.categoria],
            ['Estado',    a.estado],
            ['Inscripción', a.fecha_inscripcion],
        ];
        if (a.empleador)             afipRows.splice(1, 0, ['Empleador',  a.empleador]);
        if (a.actividad)             afipRows.splice(1, 0, ['Actividad',  a.actividad]);
        if (a.categoria_monotributo) afipRows.splice(2, 0, ['Cat. Monotributo', a.categoria_monotributo]);
        renderSimpleTable('afip-table', afipRows);

        // Propiedad
        const prop = profile.propiedad;
        const elegibleTag = prop.elegible === false
            ? '<span style="color:#b91c1c;font-weight:600;">✗ No elegible</span>'
            : '<span style="color:#15803d;font-weight:600;">✓ Elegible</span>';
        const cuotaFmt = prop.cuota_estimada
            ? `$ ${Math.round(prop.cuota_estimada).toLocaleString('es-AR')}`
            : '—';
        const ratioFmt = prop.ratio_cuota != null
            ? `${(prop.ratio_cuota * 100).toFixed(1)}% del sueldo neto`
            : '—';
        renderSimpleTable('propiedad-table', [
            ['ID',              prop.id],
            ['Dirección',       prop.direccion],
            ['Localidad',       prop.localidad],
            ['Tipo',            prop.tipo],
            ['Superficie',      `${prop.superficie_m2} m²`],
            ['Ambientes',       prop.ambientes],
            ['Precio',          `$ ${Number(prop.precio_pesos).toLocaleString('es-AR')}`],
            ['Cuota estimada',  cuotaFmt],
            ['Ratio cuota/neto', ratioFmt],
            ['Elegibilidad',    elegibleTag],
            ['Apta Hipoteca',   prop.apta_hipoteca ? '✓ Sí' : 'No'],
        ]);

        // Payslip preview — support 3-month array or single legacy string
        const texts = profile.payslip_texts || (profile.payslip_text ? [profile.payslip_text] : []);
        currentPayslipTexts = texts;
        _renderPayslipTabs(texts);

        showPersonaDetail();
    }

    // ─── Payslip tabs ─────────────────────────────────────────────
    function _renderPayslipTabs(texts) {
        const tabsEl  = document.getElementById('payslip-tabs');
        const preEl   = document.getElementById('payslip-preview');
        if (!texts || !texts.length) {
            preEl.textContent = '—';
            if (tabsEl) tabsEl.style.display = 'none';
            return;
        }

        const labels = texts.length === 3
            ? ['Dos meses atrás', 'Mes anterior', 'Más actual']
            : texts.map((_, i) => `Recibo ${i + 1}`);

        // Update tab labels and visibility
        if (tabsEl) {
            tabsEl.style.display = texts.length > 1 ? 'flex' : 'none';
            const btns = tabsEl.querySelectorAll('.payslip-tab');
            btns.forEach((btn, i) => {
                btn.textContent = labels[i] || `Recibo ${i + 1}`;
                btn.style.display = i < texts.length ? 'inline-block' : 'none';
                btn.classList.toggle('active', i === texts.length - 1);  // default: most recent
            });

            // Show most recent by default
            preEl.textContent = texts[texts.length - 1] || '—';

            // Tab click handler (re-register)
            tabsEl.querySelectorAll('.payslip-tab').forEach(btn => {
                btn.onclick = () => {
                    tabsEl.querySelectorAll('.payslip-tab').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const idx = parseInt(btn.dataset.idx, 10);
                    preEl.textContent = texts[idx] || '—';
                };
            });
        } else {
            preEl.textContent = texts[texts.length - 1] || '—';
        }
    }

    function showPersonaDetail() {
        personaDetailSec.style.display = 'block';
        resultsSection.style.display   = 'none';
        decisionPanel.style.display    = 'none';
        personaDetailSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ─── Back to list ─────────────────────────────────────────────
    function backToList() {
        personaDetailSec.style.display = 'none';
        resultsSection.style.display   = 'none';
        document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('selected'));
        currentPersonaId = null;
        lastExtractionResult = null;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ─── Analyze Persona (SSE) ────────────────────────────────────
    async function handleAnalyzePersona() {
        if (currentPersonaId === null) return;

        showLoading('Analizando solicitud…', 'Procesando datos con IA');

        try {
            const response = await fetch(`${PERSONAS_BASE_URL}/${currentPersonaId}/analyze`);
            if (!response.ok) {
                const err = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(err.detail || `Error ${response.status}`);
            }

            const reader  = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer    = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();

                for (const part of parts) {
                    const line = part.trim();
                    if (!line.startsWith('data: ')) continue;

                    try {
                        const evt = JSON.parse(line.slice(6));

                        if (evt.type === 'progress') {
                            updateLoadingStep(evt.step, evt.detail);
                            appendLoadingStep(_stepLabel(evt.step, evt.detail));
                        } else if (evt.type === 'result') {
                            lastExtractionResult = evt.data;
                            // If profile data came back in the result, refresh the detail panel
                            if (evt.data.persona_profile) {
                                renderPersonaDetail({
                                    renaper:   evt.data.persona_profile.renaper,
                                    bcra:      evt.data.persona_profile.bcra,
                                    afip:      evt.data.persona_profile.afip,
                                    propiedad: evt.data.persona_profile.propiedad,
                                    payslip_text: document.getElementById('payslip-preview').textContent,
                                });
                            }
                            displayResults(evt.data);
                        } else if (evt.type === 'error') {
                            throw new Error(evt.detail);
                        }
                    } catch (parseErr) {
                        if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr;
                    }
                }
            }
        } catch (err) {
            console.error(err);
            alert('Error durante el análisis: ' + err.message);
        } finally {
            hideLoading();
        }
    }

    // ─── Decision Handler ─────────────────────────────────────────
    async function handleDecision(decision) {
        if (currentPersonaId === null || !lastExtractionResult) return;

        const decisionLabels = { aprobar: 'Aprobar', esperar: 'Esperar', rechazar: 'Rechazar' };

        // Disable all decision buttons while sending
        ['btn-aprobar', 'btn-esperar', 'btn-rechazar'].forEach(id => {
            document.getElementById(id).disabled = true;
        });

        try {
            const res = await fetch(`${PERSONAS_BASE_URL}/${currentPersonaId}/decision`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    decision:  decision,
                    ai_result: lastExtractionResult,
                }),
            });

            const data = await res.json();

            if (data.ok) {
                showToast(`✓ Decisión "${decisionLabels[decision]}" enviada por email a ${data.email_sent_to}`, 'success');
            } else {
                showToast(`Decisión registrada, pero el email falló: ${data.email_error || 'error desconocido'}`, 'warning');
            }
        } catch (err) {
            showToast('Error al enviar la decisión: ' + err.message, 'error');
        } finally {
            // Re-enable buttons
            ['btn-aprobar', 'btn-esperar', 'btn-rechazar'].forEach(id => {
                document.getElementById(id).disabled = false;
            });
        }
    }

    // ─── Display AI Results ───────────────────────────────────────
    function displayResults(data) {
        if (rawJson) {
            rawJson.textContent = JSON.stringify(data, null, 2);
        }

        renderRecomendacion(data.recomendacion);
        renderCondiciones(data.recomendacion);

        renderFieldTable('solicitante-table', data.solicitante, [
            ['nombre_completo', 'Nombre Completo'],
            ['dni',             'DNI'],
            ['fecha_nacimiento','Fecha de Nacimiento'],
            ['domicilio',       'Domicilio'],
        ]);

        // Empleo — label sueldo_neto/bruto as "(período más reciente)" when historico exists
        const hasHistorico = data.haberes_historico && data.haberes_historico.periodos && data.haberes_historico.periodos.length > 1;
        renderFieldTable('empleo-table', data.empleo, [
            ['empleador',         'Empleador'],
            ['cuil',              'CUIL'],
            ['sueldo_bruto',      hasHistorico ? 'Sueldo Bruto (más reciente)' : 'Sueldo Bruto'],
            ['sueldo_neto',       hasHistorico ? 'Sueldo Neto (más reciente)'  : 'Sueldo Neto'],
            ['fecha_recibo',      hasHistorico ? 'Fecha Recibo (más reciente)' : 'Fecha del Recibo'],
            ['antiguedad_laboral','Antigüedad'],
            ['tipo_empleo',       'Tipo de Empleo'],
        ]);

        // Historial de Haberes
        renderHaberesHistorico(data.haberes_historico);

        renderValidaciones('validaciones-table', data.validaciones);
        renderAlertas(data);

        resultsSection.style.display = 'block';
        decisionPanel.style.display  = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ─── Historial de Haberes ─────────────────────────────────────
    function renderHaberesHistorico(historico) {
        const section    = document.getElementById('haberes-historico-section');
        const container  = document.getElementById('haberes-historico-table');
        if (!section || !container) return;

        if (!historico || !historico.periodos || !historico.periodos.length) {
            section.style.display = 'none';
            return;
        }
        section.style.display = 'block';

        const tendencia    = historico.tendencia    || '';
        const consistencia = historico.consistencia || '';
        const promedio     = historico.promedio_neto_pesos;

        const tendenciaIcon = tendencia === 'creciente'   ? '↑ Creciente'
                            : tendencia === 'decreciente' ? '↓ Decreciente'
                            : tendencia === 'estable'     ? '→ Estable'
                            : '—';
        const tendenciaClass = tendencia === 'creciente'   ? 'status-ok'
                             : tendencia === 'decreciente' ? 'status-alerta'
                             : '';
        const consistenciaClass = consistencia === 'OK' ? 'status-ok'
                                : consistencia === 'ALERTA' ? 'status-alerta' : '';

        const promedioFmt = promedio != null
            ? `$ ${Math.round(promedio).toLocaleString('es-AR')}`
            : '—';

        // Periods table
        let periodsHtml = `
            <table class="field-table haberes-historico-tbl">
                <thead><tr>
                    <th>Período</th>
                    <th>Empleador</th>
                    <th>Sueldo Bruto</th>
                    <th>Sueldo Neto</th>
                </tr></thead>
                <tbody>`;
        historico.periodos.forEach((p, idx) => {
            const isLatest = idx === historico.periodos.length - 1;
            periodsHtml += `<tr${isLatest ? ' class="haberes-row-latest"' : ''}>
                <td>${escHtml(p.periodo || '—')}${isLatest ? ' <span class="badge-reciente">reciente</span>' : ''}</td>
                <td>${escHtml(p.empleador || '—')}</td>
                <td>${escHtml(p.sueldo_bruto || '—')}</td>
                <td><strong>${escHtml(p.sueldo_neto || '—')}</strong></td>
            </tr>`;
        });
        periodsHtml += `</tbody></table>`;

        // Stats row
        const statsHtml = `
            <div class="haberes-stats-row">
                <div class="haberes-stat">
                    <span class="haberes-stat-label">Promedio neto</span>
                    <span class="haberes-stat-value">${escHtml(promedioFmt)}</span>
                </div>
                <div class="haberes-stat">
                    <span class="haberes-stat-label">Tendencia</span>
                    <span class="haberes-stat-value ${tendenciaClass}">${escHtml(tendenciaIcon)}</span>
                </div>
                <div class="haberes-stat">
                    <span class="haberes-stat-label">Consistencia</span>
                    <span class="haberes-stat-value ${consistenciaClass}">${escHtml(consistencia || '—')}</span>
                </div>
            </div>`;

        container.innerHTML = periodsHtml + statsHtml;
    }

    // ─── Recommendation Panel ─────────────────────────────────────
    function renderRecomendacion(rec) {
        if (!rec) return;
        const panel    = document.getElementById('recomendacion-panel');
        const light    = document.getElementById('semaforo-light');
        const label    = document.getElementById('semaforo-label');
        const decision = document.getElementById('recomendacion-decision');
        const resumen  = document.getElementById('recomendacion-resumen');
        const razonesEl = document.getElementById('recomendacion-razones');

        const estado = (rec.estado || 'AMARILLO').toUpperCase();
        const cls    = estado === 'VERDE' ? 'verde'
                     : estado === 'ROJO'  ? 'rojo'
                     : 'amarillo';

        panel.className     = 'recomendacion-panel ' + cls;
        light.className     = 'semaforo-light ' + cls;
        label.className     = 'semaforo-label ' + cls;
        label.textContent   = estado;

        const decisionMap = {
            'APROBAR':  'Sugerencia: Aprobar',
            'REVISAR':  'Sugerencia: Revisar',
            'RECHAZAR': 'Sugerencia: Rechazar',
        };
        decision.textContent = decisionMap[rec.decision] || rec.decision || '—';
        resumen.textContent  = rec.resumen || '';

        razonesEl.innerHTML = '';
        (Array.isArray(rec.razones) ? rec.razones : []).forEach(r => {
            const li = document.createElement('li');
            li.textContent = r;
            razonesEl.appendChild(li);
        });
    }

    // ─── Conditions Observed ──────────────────────────────────────
    function renderCondiciones(rec) {
        const list = document.getElementById('condiciones-list');
        list.innerHTML = '';
        const conds = rec && Array.isArray(rec.condiciones_observadas) ? rec.condiciones_observadas : [];
        if (!conds.length) {
            list.innerHTML = '<li style="color:#9ca3af;">Sin condiciones registradas.</li>';
            return;
        }
        conds.forEach(c => {
            const li = document.createElement('li');
            li.textContent = c;
            list.appendChild(li);
        });
    }

    // ─── Generic field table ──────────────────────────────────────
    function renderFieldTable(containerId, sectionData, fields) {
        const container = document.getElementById(containerId);
        if (!sectionData) {
            container.innerHTML = '<p style="color:#9ca3af;font-size:0.82rem;margin:0;">Sin datos</p>';
            return;
        }
        let html = '<table class="field-table"><tbody>';
        for (const [key, label] of fields) {
            const val     = sectionData[key];
            const isArray = Array.isArray(val);
            const raw     = isArray ? val.join(', ') : (val ?? '');
            const isEmpty = raw === '' || raw === null || raw === undefined;
            const display = isEmpty
                ? '<span class="field-empty">—</span>'
                : escHtml(String(raw));
            html += `<tr><td>${escHtml(label)}</td><td>${display}</td></tr>`;
        }
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // ─── Simple key-value table (for profile) ────────────────────
    function renderSimpleTable(containerId, rows) {
        const container = document.getElementById(containerId);
        if (!rows || !rows.length) {
            container.innerHTML = '<p class="no-data">Sin datos</p>';
            return;
        }
        let html = '<table class="field-table"><tbody>';
        rows.forEach(([label, val]) => {
            const empty = val === '' || val === null || val === undefined;
            // Values that start with '<' are pre-built HTML snippets (e.g. badges)
            // and should not be escaped.
            const isHtml = typeof val === 'string' && val.trimStart().startsWith('<');
            const display = empty
                ? '<span class="field-empty">—</span>'
                : isHtml ? val : escHtml(String(val));
            html += `<tr><td>${escHtml(label)}</td><td>${display}</td></tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // ─── Validaciones ─────────────────────────────────────────────
    function renderValidaciones(containerId, validaciones) {
        const container = document.getElementById(containerId);
        if (!validaciones) {
            container.innerHTML = '<p style="color:#9ca3af;font-size:0.82rem;margin:0;">Sin datos</p>';
            return;
        }
        const rows = [
            ['nombres_coinciden',   'Coincidencia de Nombres'],
            ['detalle_coincidencia','Detalle'],
            ['recibo_vigente',      'Vigencia del Recibo'],
        ];
        let html = '<table class="field-table"><tbody>';
        for (const [key, label] of rows) {
            const val     = validaciones[key] ?? '';
            const cls     = statusClass(val);
            const display = val === ''
                ? '<span class="field-empty">—</span>'
                : `<span class="${cls}">${escHtml(val)}</span>`;
            html += `<tr><td>${escHtml(label)}</td><td>${display}</td></tr>`;
        }
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    function statusClass(val) {
        if (!val) return '';
        const u = val.toUpperCase();
        if (u === 'OK') return 'status-ok';
        if (u.startsWith('ALERTA')) return 'status-alerta';
        if (u.includes('NO VERIFICABLE')) return 'status-no-verificable';
        return '';
    }

    // ─── Alertas ──────────────────────────────────────────────────
    function renderAlertas(data) {
        const alertasSection   = document.getElementById('alertas-section');
        const alertasContainer = document.getElementById('alertas-container');
        const all = [];
        [
            { data: data.solicitante,  key: 'alertas_solicitante' },
            { data: data.empleo,       key: 'alertas_empleo'       },
            { data: data.validaciones, key: 'alertas_validacion'   },
            { data: data.metadatos,    key: 'alertas_generales'    },
        ].forEach(({ data: d, key }) => {
            if (d && Array.isArray(d[key])) d[key].forEach(a => all.push(a));
        });
        if (!all.length) {
            alertasSection.style.display = 'none';
            return;
        }
        alertasSection.style.display = 'block';
        let html = '<ul class="alertas-list">';
        all.forEach(a => { html += `<li>${escHtml(a)}</li>`; });
        html += '</ul>';
        alertasContainer.innerHTML = html;
    }

    // ─── Toast Notification ───────────────────────────────────────
    function showToast(message, type = 'success') {
        const toast = document.getElementById('toast-notification');
        toast.textContent  = message;
        toast.className    = `toast-notification toast-${type}`;
        toast.style.display = 'block';
        // Auto-hide after 5 seconds
        setTimeout(() => { toast.style.display = 'none'; }, 5000);
    }

    // ─── Actions ──────────────────────────────────────────────────
    function copyResultsToClipboard() {
        if (!lastExtractionResult) return;
        navigator.clipboard.writeText(JSON.stringify(lastExtractionResult, null, 2)).then(() => {
            const btn = document.getElementById('copy-results');
            const orig = btn.textContent;
            btn.textContent = '✓ Copiado';
            setTimeout(() => (btn.textContent = orig), 2000);
        });
    }

    function downloadJson() {
        if (!lastExtractionResult) return;
        const blob     = new Blob([JSON.stringify(lastExtractionResult, null, 2)], { type: 'application/json' });
        const filename = `solicitud_${new Date().toISOString().slice(0, 10)}.json`;
        const url      = URL.createObjectURL(blob);
        const a        = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
    }

    // ─── Loading Helpers ──────────────────────────────────────────
    function showLoading(text, detail) {
        loadingText.textContent    = text || 'Procesando…';
        loadingDetail.textContent  = detail || '';
        loadingSteps.innerHTML     = '';
        loadingOverlay.style.display = 'flex';
    }

    function updateLoadingStep(step, detail) {
        loadingText.textContent   = _stepLabel(step, detail);
        loadingDetail.textContent = detail || '';
    }

    function appendLoadingStep(text) {
        const item = document.createElement('div');
        item.className   = 'loading-step-item';
        item.textContent = text;
        loadingSteps.appendChild(item);
        loadingSteps.scrollTop = loadingSteps.scrollHeight;
    }

    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }

    const _STEP_LABELS = {
        generating:           'Generando 3 recibos del solicitante…',
        transcription_dni:    'Transcribiendo DNI…',
        transcription_recibo: 'Transcribiendo Recibo de Sueldo…',
        transcribing:         'Transcribiendo página…',
        cached:               'Usando caché de transcripción…',
        extraction:           'Extrayendo entidades con IA…',
    };

    function _stepLabel(step, detail) {
        return _STEP_LABELS[step] || detail || step;
    }

    // ─── Utility ──────────────────────────────────────────────────
    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function initials(name) {
        return name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
    }
});
