(function () {
    'use strict';

    var PROGRAMS_PER_PAGE = 6;

    var root = document.querySelector('[data-dashboard]');
    if (!root) {
        return;
    }

    var state = {
        level: root.dataset.level || 'global',
        importId: root.dataset.importId || '',
        programId: root.dataset.programId || '',
        studentRef: root.dataset.studentRef || '',
        year: root.dataset.year || '',
        simulation: root.dataset.simulation || '',
        subject: root.dataset.subject || 'global',
        page: parsePositiveInteger(root.dataset.page, 1),
        studentSearch: '',
        overview: null,
        program: null,
        student: null,
        filters: null,
        competencyOptions: [],
        selectedProgramId: '',
        programFilterData: null,
        requestNumber: 0,
        selectedProgramRequest: 0,
        searchTimer: null
    };

    var content = root.querySelector('[data-dashboard-content]');
    var loading = root.querySelector('[data-dashboard-loading]');
    var errorBox = root.querySelector('[data-dashboard-error]');
    var noImport = root.querySelector('[data-dashboard-no-import]');
    var yearFilter = root.querySelector('[data-filter-year]');
    var subjectFilter = root.querySelector('[data-filter-subject]');
    var simulationFilter = root.querySelector('[data-filter-simulation]');
    var programFilter = root.querySelector('[data-program-filter]');

    function parsePositiveInteger(value, fallback) {
        var parsed = Number.parseInt(value, 10);
        return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
    }

    function showState(name) {
        loading.hidden = name !== 'loading';
        errorBox.hidden = name !== 'error';
        noImport.hidden = name !== 'empty';
        content.hidden = name !== 'content';
    }

    function errorMessage(error) {
        var detail = error && error.data ? error.data.detail : null;
        if (typeof detail === 'string') {
            return detail;
        }
        if (detail && typeof detail.message === 'string') {
            return detail.message;
        }
        if (error && error.status === 403) {
            return 'Tu cuenta no tiene permiso para consultar estos resultados.';
        }
        if (error && error.status === 404) {
            return 'No hay una importación activa o la información solicitada ya no está disponible.';
        }
        return 'Verifica que la API esté disponible e inténtalo nuevamente.';
    }

    function makeError(message, status, data) {
        var error = new Error(message);
        error.status = status;
        error.data = data;
        return error;
    }

    function apiRequest(params, options) {
        var url = new URL('partials/dashboard/data.php', window.location.href);
        Object.keys(params || {}).forEach(function (key) {
            var value = params[key];
            if (value !== '' && value !== null && value !== undefined) {
                url.searchParams.set(key, String(value));
            }
        });

        var requestOptions = Object.assign({
            headers: {
                Accept: 'application/json',
                'X-Dashboard-Request': '1'
            }
        }, options || {});

        return fetch(url.toString(), requestOptions).then(function (response) {
            return response.json().catch(function () {
                throw makeError('La aplicación recibió una respuesta no válida.', response.status);
            }).then(function (data) {
                if (response.status === 401) {
                    window.location.assign('login.php');
                    throw makeError('La sesión expiró.', 401, data);
                }
                if (!response.ok) {
                    throw makeError(errorMessage({ status: response.status, data: data }), response.status, data);
                }
                return data;
            });
        });
    }

    function buildFilterParams() {
        return {
            year: state.year,
            simulation: state.simulation
        };
    }

    function dashboardUrl() {
        var url = new URL('index.php', window.location.href);
        url.searchParams.set('view', 'dashboard');
        url.searchParams.set('level', state.level);
        if (state.importId) {
            url.searchParams.set('import_id', state.importId);
        }
        if (state.year) {
            url.searchParams.set('year', state.year);
        }
        if (state.simulation) {
            url.searchParams.set('simulation', state.simulation);
        }
        if (state.subject && state.subject !== 'global') {
            url.searchParams.set('subject', state.subject);
        }

        if (state.level === 'program' || state.level === 'student') {
            url.searchParams.set('program_id', state.programId);
            url.searchParams.set('page', String(state.page));
        } else {
            if (state.page > 1) {
                url.searchParams.set('page', String(state.page));
            }
            if (state.selectedProgramId) {
                url.searchParams.set('program_filter', state.selectedProgramId);
            }
        }
        if (state.studentSearch) {
            url.searchParams.set('search', state.studentSearch);
        }
        if (state.level === 'student' && state.studentRef) {
            url.searchParams.set('student_ref', state.studentRef);
        }
        return url;
    }

    function updateUrl(replace) {
        var url = dashboardUrl();
        if (replace) {
            window.history.replaceState({}, '', url);
        } else {
            window.history.pushState({}, '', url);
        }
    }

    function readUrlState() {
        var params = new URLSearchParams(window.location.search);
        state.level = params.get('level') || 'global';
        state.importId = params.get('import_id') || '';
        state.programId = params.get('program_id') || '';
        state.studentRef = params.get('student_ref') || '';
        state.year = params.get('year') || '';
        state.simulation = params.get('simulation') || '';
        state.subject = params.get('subject') || 'global';
        state.page = parsePositiveInteger(params.get('page'), 1);
        state.studentSearch = params.get('search') || '';
        state.selectedProgramId = params.get('program_filter') || '';
        if (!['global', 'program', 'student'].includes(state.level)) {
            state.level = 'global';
        }
    }

    function formatNumber(value) {
        if (typeof value !== 'number' || !Number.isFinite(value)) {
            return 'Sin datos';
        }
        return new Intl.NumberFormat('es-CO', {
            maximumFractionDigits: 2
        }).format(value);
    }

    function numberOrNull(value) {
        return typeof value === 'number' && Number.isFinite(value) ? value : null;
    }

    function setText(selector, value) {
        var element = root.querySelector(selector);
        if (element) {
            element.textContent = value === null || value === undefined ? '' : String(value);
        }
    }

    function addOption(select, value, label) {
        var option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }

    function populateSelect(select, options, selected, allLabel) {
        select.replaceChildren();
        if (allLabel !== null) {
            addOption(select, '', allLabel);
        }
        options.forEach(function (option) {
            addOption(select, String(option.value), option.label);
        });
        var available = Array.prototype.some.call(select.options, function (option) {
            return option.value === selected;
        });
        select.value = available ? selected : (allLabel === null ? (select.options[0] ? select.options[0].value : '') : '');
        return available;
    }

    function competencyEntries(metrics) {
        var competencies = metrics && metrics.competencies ? metrics.competencies : {};
        return Object.keys(competencies).map(function (key) {
            return {
                key: key,
                label: competencies[key].label || key,
                value: numberOrNull(competencies[key].average)
            };
        });
    }

    function configureFilters(overview) {
        state.filters = overview.filters || state.filters;
        var years = (state.filters && state.filters.years ? state.filters.years : []).map(function (year) {
            return { value: year, label: String(year) };
        });
        var simulations = (state.filters && state.filters.simulations ? state.filters.simulations : []).map(function (simulation) {
            return { value: simulation, label: simulation };
        });

        var validYear = populateSelect(yearFilter, years, state.year, 'Todos');
        if (!validYear) {
            state.year = '';
        }
        var validSimulation = populateSelect(simulationFilter, simulations, state.simulation, 'Todos');
        if (!validSimulation) {
            state.simulation = '';
        }

        var metrics = overview.kpis || overview.metrics;
        var competencies = competencyEntries(metrics);
        if (competencies.length) {
            state.competencyOptions = competencies;
        }
        var subjectOptions = [
            { value: 'global', label: 'Global' },
            { value: 'all', label: 'Todas las asignaturas' }
        ].concat(state.competencyOptions.map(function (item) {
            return { value: item.key, label: item.label };
        }));
        var validSubject = populateSelect(subjectFilter, subjectOptions, state.subject, null);
        if (!validSubject) {
            state.subject = 'global';
            subjectFilter.value = 'global';
        }

        if (Array.isArray(overview.programs)) {
            var programs = overview.programs;
            populateSelect(programFilter, programs.map(function (item) {
                return { value: item.program_id, label: item.name };
            }), state.selectedProgramId, 'Todos los programas');
            if (!programs.some(function (item) { return String(item.program_id) === state.selectedProgramId; })) {
                state.selectedProgramId = '';
                programFilter.value = '';
            }
        }
        updateFilterContext();
    }

    function updateFilterContext() {
        var context = root.querySelector('[data-filter-context]');
        var values = [];
        if (state.year) {
            values.push('Año: ' + state.year);
        }
        if (state.simulation) {
            values.push('Simulacro: ' + state.simulation);
        }
        if (state.subject === 'all') {
            values.push('Asignatura: Todas');
        } else if (state.subject !== 'global') {
            var subject = state.competencyOptions.find(function (item) {
                return item.key === state.subject;
            });
            if (subject) {
                values.push('Asignatura: ' + subject.label);
            }
        } else {
            values.push('Asignatura: Global');
        }
        context.textContent = values.join(' · ');
    }

    function chartElement(svg, name, attributes, parent) {
        var element = document.createElementNS('http://www.w3.org/2000/svg', name);
        Object.keys(attributes || {}).forEach(function (key) {
            element.setAttribute(key, attributes[key]);
        });
        (parent || svg).appendChild(element);
        return element;
    }

    function chartText(svg, text, x, y, className, parent) {
        var node = chartElement(svg, 'text', {
            x: x,
            y: y,
            class: className || 'chart-label'
        }, parent);
        node.textContent = text;
        return node;
    }

    function prepareSvg(svg, title, description, viewBox) {
        svg.replaceChildren();
        svg.setAttribute('viewBox', viewBox);
        svg.setAttribute('preserveAspectRatio', 'xMinYMin meet');
        svg.setAttribute('aria-label', description);
        var titleNode = chartElement(svg, 'title', {});
        titleNode.textContent = title;
        var descriptionNode = chartElement(svg, 'desc', {});
        descriptionNode.textContent = description;
    }

    function selectedMetric(metrics) {
        if (!metrics) {
            return null;
        }
        if (state.subject === 'global' || state.subject === 'all') {
            return numberOrNull(metrics.average_global);
        }
        var competency = metrics.competencies && metrics.competencies[state.subject];
        return competency ? numberOrNull(competency.average) : null;
    }

    function selectedMetricLabel() {
        if (state.subject === 'global' || state.subject === 'all') {
            return 'Promedio global';
        }
        var selected = state.competencyOptions.find(function (item) {
            return item.key === state.subject;
        });
        return selected ? selected.label : 'Promedio global';
    }

    function drawBubbles(programs) {
        var container = root.querySelector('[data-program-bubbles]');
        var empty = root.querySelector('[data-empty-bubbles]');
        container.replaceChildren();
        if (!programs.length) {
            empty.hidden = false;
            return;
        }
        empty.hidden = true;
        programs.forEach(function (program) {
            var card = document.createElement('button');
            card.type = 'button';
            card.className = 'program-card';
            card.setAttribute('aria-label', program.name + ', ' + selectedMetricLabel() + ': ' + formatNumber(selectedMetric(program.metrics)));

            var name = document.createElement('span');
            name.className = 'program-card-name';
            name.textContent = program.name;
            card.appendChild(name);

            var label = document.createElement('span');
            label.className = 'program-card-metric-label';
            label.textContent = selectedMetricLabel();
            card.appendChild(label);

            var value = document.createElement('strong');
            value.className = 'program-card-metric';
            value.textContent = formatNumber(selectedMetric(program.metrics));
            card.appendChild(value);

            card.addEventListener('click', function () {
                openProgram(program.program_id);
            });
            container.appendChild(card);
        });
    }

    function truncate(value, limit) {
        var text = String(value || '');
        return text.length > limit ? text.slice(0, limit - 1) + '…' : text;
    }

    function drawBars(svg, entries, title, description, emptyElement) {
        var validEntries = entries.filter(function (entry) {
            return numberOrNull(entry.value) !== null;
        });
        if (!validEntries.length) {
            svg.replaceChildren();
            if (emptyElement) {
                emptyElement.hidden = false;
            }
            return;
        }
        if (emptyElement) {
            emptyElement.hidden = true;
        }

        var width = 900;
        var rowHeight = 39;
        var top = 26;
        var height = top + validEntries.length * rowHeight + 16;
        var labelWidth = validEntries.length > 10 ? 190 : 220;
        var barWidth = width - labelWidth - 80;
        var maxValue = Math.max.apply(null, validEntries.map(function (item) {
            return item.value;
        }));
        if (maxValue <= 0) {
            maxValue = 1;
        }
        prepareSvg(svg, title, description, '0 0 ' + width + ' ' + height);

        [0, 0.25, 0.5, 0.75, 1].forEach(function (fraction) {
            var x = labelWidth + fraction * barWidth;
            chartElement(svg, 'line', {
                x1: x,
                y1: 17,
                x2: x,
                y2: height - 11,
                class: 'chart-grid-line'
            });
            chartText(svg, formatNumber(maxValue * fraction), x, 12, 'chart-axis-label');
        });

        validEntries.forEach(function (entry, index) {
            var y = top + index * rowHeight;
            chartText(svg, truncate(entry.label, 31), labelWidth - 12, y + 15, 'chart-row-label');
            chartElement(svg, 'rect', {
                x: labelWidth,
                y: y + 3,
                width: Math.max(2, barWidth * entry.value / maxValue),
                height: 18,
                rx: 4,
                class: 'chart-bar'
            });
            chartText(svg, formatNumber(entry.value), labelWidth + barWidth * entry.value / maxValue + 8, y + 17, 'chart-value-label');
        });
    }

    function programCompetencyEntries(metrics) {
        var competencies = competencyEntries(metrics);
        if (state.subject === 'global' || state.subject === 'all') {
            return competencies;
        }
        return competencies.filter(function (item) {
            return item.key === state.subject;
        });
    }

    function renderSelectedProgram(program) {
        var panel = root.querySelector('[data-selected-program-panel]');
        state.programFilterData = program;
        if (!program) {
            panel.hidden = true;
            return;
        }
        panel.hidden = false;
        setText('[data-selected-program-name]', program.program.name);
        setText('[data-selected-program-average]', formatNumber(program.metrics.average_global));
        var link = root.querySelector('[data-open-selected-program]');
        link.href = dashboardUrlForProgram(program.program.program_id);
        var entries = programCompetencyEntries(program.metrics);
        drawBars(
            root.querySelector('[data-selected-program-chart]'),
            entries,
            'Resultados de ' + program.program.name,
            'Promedios de las asignaturas que devuelve la API.',
            null
        );
    }

    function dashboardUrlForProgram(programId) {
        var url = dashboardUrl();
        url.searchParams.set('level', 'program');
        url.searchParams.set('program_id', programId);
        url.searchParams.delete('program_filter');
        url.searchParams.delete('page');
        url.searchParams.delete('search');
        url.searchParams.delete('student_ref');
        return url.toString();
    }

    function renderOverview(overview, loadSelected) {
        state.overview = overview;
        state.filters = overview.filters || state.filters;
        configureFilters(overview);
        setText('[data-kpi-average]', formatNumber(overview.kpis.average_global));
        setText('[data-kpi-programs]', formatNumber(overview.kpis.programs));
        setText('[data-kpi-students]', formatNumber(overview.kpis.unique_students));
        setText('[data-kpi-presentations]', formatNumber(overview.kpis.presentations));

        var programs = overview.programs || [];
        var totalPages = Math.max(1, Math.ceil(programs.length / PROGRAMS_PER_PAGE));
        if (state.page > totalPages) {
            state.page = totalPages;
            updateUrl(true);
        }
        var start = (state.page - 1) * PROGRAMS_PER_PAGE;
        drawBubbles(programs.slice(start, start + PROGRAMS_PER_PAGE));

        var totalPrograms = overview.total_programs;
        setText('[data-program-page-label]', totalPrograms + ' programas');
        setText('[data-program-pages]', 'Página ' + state.page + ' de ' + totalPages + ' · ' + totalPrograms + ' programas');
        root.querySelector('[data-program-prev]').disabled = state.page <= 1;
        root.querySelector('[data-program-next]').disabled = state.page >= totalPages;
        root.querySelector('[data-program-pagination]').hidden = totalPages <= 1;

        if (programFilter.value !== state.selectedProgramId) {
            programFilter.value = state.selectedProgramId;
        }
        if (state.selectedProgramId && loadSelected) {
            loadSelectedProgram();
        } else if (state.selectedProgramId && state.programFilterData) {
            renderSelectedProgram(state.programFilterData);
        } else {
            if (!state.selectedProgramId) {
                state.selectedProgramRequest += 1;
                renderSelectedProgram(null);
            }
        }
    }

    function renderProgram(program) {
        state.program = program;
        state.filters = program.filters || state.filters;
        configureFilters({ filters: program.filters, metrics: program.metrics });
        setText('[data-program-title]', program.program.name);
        setText('[data-program-average]', formatNumber(program.metrics.average_global));
        setText('[data-program-students-count]', formatNumber(program.metrics.unique_students));
        setText('[data-program-presentations]', formatNumber(program.metrics.presentations));

        var competencies = programCompetencyEntries(program.metrics);
        drawBars(
            root.querySelector('[data-program-competencies]'),
            competencies,
            'Desempeño de ' + program.program.name,
            'Resultados por asignatura calculados por la API.',
            root.querySelector('[data-empty-program-competencies]')
        );
        renderProgramStudents(program);
        setText('[data-student-search-status]', state.studentSearch ? 'Búsqueda activa' : '');
        var backLink = root.querySelector('[data-back-global]');
        backLink.href = dashboardUrlForGlobal();
    }

    function dashboardUrlForGlobal() {
        var url = dashboardUrl();
        url.searchParams.set('level', 'global');
        url.searchParams.delete('program_id');
        url.searchParams.delete('student_ref');
        url.searchParams.delete('search');
        url.searchParams.delete('page');
        return url.toString();
    }

    function renderProgramStudents(program) {
        var tbody = root.querySelector('[data-program-students]');
        var empty = root.querySelector('[data-empty-students]');
        tbody.replaceChildren();
        var students = program.students || [];
        students.forEach(function (student) {
            var row = document.createElement('tr');
            addCell(row, student.name || 'Nombre no disponible', 'student-name-cell');
            addCell(row, student.document || 'Sin documento');
            addCell(row, student.year);
            addCell(row, student.simulation || 'Sin dato');
            addCell(row, formatNumber(student.global_score));
            addCell(row, student.presented === true ? 'Presentó' : (student.presented === false ? 'No presentó' : 'Sin dato'));
            var actionCell = document.createElement('td');
            if (student.document) {
                var button = document.createElement('button');
                button.type = 'button';
                button.className = 'text-button student-open-button';
                button.textContent = 'Ver detalle →';
                button.addEventListener('click', function () {
                    openStudent(student.document);
                });
                actionCell.appendChild(button);
            } else {
                actionCell.textContent = 'Sin documento';
            }
            row.appendChild(actionCell);
            tbody.appendChild(row);
        });
        empty.hidden = students.length > 0;
        var pageLabel = 'Página ' + program.page + ' de ' + program.total_pages + ' · ' + program.total_records + ' registros';
        setText('[data-student-pages]', pageLabel);
        root.querySelector('[data-student-prev]').disabled = program.page <= 1;
        root.querySelector('[data-student-next]').disabled = program.page >= program.total_pages;
        root.querySelector('.student-pagination').hidden = program.total_records === 0;
    }

    function addCell(row, value, className) {
        var cell = document.createElement('td');
        if (className) {
            cell.className = className;
        }
        cell.textContent = value === null || value === undefined ? '—' : String(value);
        row.appendChild(cell);
    }

    function renderStudent(student) {
        state.student = student;
        var program = student.programs.find(function (item) {
            return item.program_id === state.programId;
        });
        var history = (student.history || []).filter(function (attempt) {
            return attempt.program_id === state.programId &&
                (!state.year || String(attempt.year) === state.year) &&
                (!state.simulation || attempt.simulation === state.simulation);
        });
        var latest = history.length ? history[history.length - 1] : null;
        setText('[data-student-title]', student.name || 'Estudiante');
        setText('[data-student-document]', student.document ? 'Documento: ' + student.document : 'Documento no disponible');
        setText('[data-student-program]', program ? program.name : (latest ? latest.program : 'Programa no disponible'));
        setText('[data-student-attempts]', formatNumber(history.length));

        var score;
        var scoreLabel;
        if (!latest) {
            score = null;
            scoreLabel = state.subject === 'global' || state.subject === 'all' ? 'Puntaje global' : selectedMetricLabel();
        } else if (state.subject === 'global' || state.subject === 'all') {
            score = numberOrNull(latest.global_score);
            scoreLabel = 'Puntaje global';
        } else {
            score = latest.scores ? numberOrNull(latest.scores[state.subject]) : null;
            scoreLabel = selectedMetricLabel();
        }
        setText('[data-student-score-label]', scoreLabel);
        setText('[data-student-score]', formatNumber(score));
        setText('[data-student-program-average]', (state.subject === 'global' || state.subject === 'all') && latest
            ? formatNumber(latest.program_average_global)
            : 'No disponible');

        if (state.subject === 'all' && latest && latest.scores) {
            var metricEntries = state.competencyOptions.map(function (competency) {
                return {
                    label: competency.label,
                    value: numberOrNull(latest.scores[competency.key])
                };
            });
            setText('[data-student-chart-title]', 'Resultados por asignatura · último intento');
            drawBars(
                root.querySelector('[data-student-history]'),
                metricEntries,
                'Resultados por asignatura de ' + (student.name || 'estudiante'),
                'Puntajes del último intento en las asignaturas disponibles.',
                root.querySelector('[data-empty-history]')
            );
        } else {
            var subjectKey = state.subject === 'global' ? null : state.subject;
            var subjectName = state.subject === 'global' ? 'Global' : selectedMetricLabel();
            setText('[data-student-chart-title]', 'Evolución · ' + subjectName);
            var historyEntries = history.map(function (attempt) {
                var value = subjectKey === null
                    ? numberOrNull(attempt.global_score)
                    : numberOrNull(attempt.scores && attempt.scores[subjectKey]);
                return {
                    label: String(attempt.year) + ' · ' + (attempt.simulation || 'Simulacro'),
                    value: value
                };
            });
            drawStudentTrend(
                root.querySelector('[data-student-history]'),
                historyEntries,
                student.name || 'estudiante',
                root.querySelector('[data-empty-history]')
            );
        }

        var scoresContainer = root.querySelector('[data-student-scores]');
        scoresContainer.replaceChildren();
        if (latest) {
            setText('[data-student-attempt-context]', String(latest.year) + ' · ' + latest.simulation);
            var entries = [{ label: 'Global', value: numberOrNull(latest.global_score) }];
            state.competencyOptions.forEach(function (competency) {
                entries.push({
                    label: competency.label,
                    value: numberOrNull(latest.scores && latest.scores[competency.key]),
                    level: latest.levels && latest.levels[competency.key]
                });
            });
            entries.forEach(function (entry) {
                var card = document.createElement('div');
                card.className = 'student-score-item';
                var label = document.createElement('span');
                label.textContent = entry.label;
                var value = document.createElement('strong');
                value.textContent = formatNumber(entry.value);
                card.appendChild(label);
                card.appendChild(value);
                if (entry.level) {
                    var level = document.createElement('small');
                    level.textContent = entry.level === 'Sin resultado' ? entry.level : 'Nivel ' + entry.level;
                    card.appendChild(level);
                }
                scoresContainer.appendChild(card);
            });
        } else {
            setText('[data-student-attempt-context]', 'Sin intentos para estos filtros');
            var emptyMessage = document.createElement('p');
            emptyMessage.className = 'empty-detail-message';
            emptyMessage.textContent = 'No hay resultados para este estudiante en los filtros seleccionados.';
            scoresContainer.appendChild(emptyMessage);
        }
        root.querySelector('[data-back-program]').href = dashboardUrlForProgram(state.programId);
        updateFilterContext();
    }

    function drawStudentTrend(svg, entries, studentName, emptyElement) {
        var values = entries.filter(function (entry) {
            return numberOrNull(entry.value) !== null;
        });
        if (!values.length) {
            svg.replaceChildren();
            emptyElement.hidden = false;
            return;
        }
        emptyElement.hidden = true;
        var width = Math.max(720, values.length * 105);
        var height = 330;
        var left = 55;
        var right = 25;
        var top = 24;
        var bottom = 68;
        var plotWidth = width - left - right;
        var plotHeight = height - top - bottom;
        var scores = values.map(function (entry) { return entry.value; });
        var minimum = Math.min.apply(null, scores);
        var maximum = Math.max.apply(null, scores);
        if (minimum === maximum) {
            minimum = minimum - 1;
            maximum = maximum + 1;
        }
        prepareSvg(
            svg,
            'Evolución del desempeño de ' + studentName,
            'Cada punto es un resultado individual. No se promedian intentos.',
            '0 0 ' + width + ' ' + height
        );

        for (var tick = 0; tick <= 4; tick += 1) {
            var fraction = tick / 4;
            var y = top + plotHeight * fraction;
            var score = maximum - (maximum - minimum) * fraction;
            chartElement(svg, 'line', {
                x1: left,
                y1: y,
                x2: width - right,
                y2: y,
                class: 'chart-grid-line'
            });
            chartText(svg, formatNumber(score), left - 9, y + 4, 'chart-axis-label');
        }

        var points = values.map(function (entry, index) {
            var x = values.length === 1
                ? left + plotWidth / 2
                : left + plotWidth * index / (values.length - 1);
            var y = top + plotHeight * (maximum - entry.value) / (maximum - minimum);
            return { x: x, y: y, entry: entry };
        });
        chartElement(svg, 'polyline', {
            points: points.map(function (point) { return point.x + ',' + point.y; }).join(' '),
            class: 'student-trend-line'
        });
        points.forEach(function (point) {
            var circle = chartElement(svg, 'circle', {
                cx: point.x,
                cy: point.y,
                r: 5,
                class: 'student-trend-point'
            });
            var title = chartElement(svg, 'title', {}, circle);
            title.textContent = point.entry.label + ': ' + formatNumber(point.entry.value);
            chartText(svg, truncate(point.entry.label, 14), point.x, height - 31, 'chart-axis-label');
        });
    }

    function renderCurrentData() {
        root.querySelectorAll('[data-level-view]').forEach(function (view) {
            view.hidden = view.dataset.levelView !== state.level;
        });
        if (state.level === 'global' && state.overview) {
            renderOverview(state.overview, false);
        } else if (state.level === 'program' && state.program) {
            renderProgram(state.program);
        } else if (state.level === 'student' && state.student) {
            renderStudent(state.student);
        }
        updateFilterContext();
    }

    function fetchOverview(requestNumber) {
        return apiRequest(Object.assign({
            resource: 'overview',
            import_id: state.importId,
            page: 1
        }, buildFilterParams())).then(function (overview) {
            if (requestNumber === undefined || requestNumber === state.requestNumber) {
                state.overview = overview;
                state.importId = overview.import_id;
                state.filters = overview.filters;
            }
            return overview;
        });
    }

    function fetchProgram(requestNumber) {
        return apiRequest(Object.assign({
            resource: 'program',
            import_id: state.importId,
            program_id: state.programId,
            page: state.page,
            search: state.studentSearch
        }, buildFilterParams())).then(function (program) {
            if (requestNumber === undefined || requestNumber === state.requestNumber) {
                state.program = program;
                state.filters = program.filters;
            }
            return program;
        });
    }

    function fetchStudent() {
        if (!state.studentRef) {
            return Promise.reject(makeError('Selecciona de nuevo el estudiante para consultar su historial.', 404));
        }
        return apiRequest({ resource: 'student', ref: state.studentRef }).then(function (student) {
            state.student = student;
            return student;
        });
    }

    function loadCurrentView() {
        var requestNumber = ++state.requestNumber;
        showState('loading');
        var request;
        if (state.importId) {
            request = requestCurrentData(requestNumber);
        } else {
            request = apiRequest({ resource: 'active' }).then(function (result) {
                state.importId = result.import_id;
                state.filters = result.filters;
                state.overview = result.overview;
                if (state.level === 'program') {
                    return fetchProgram(requestNumber);
                }
                if (state.level === 'student') {
                    if (!state.filters || !state.competencyOptions.length) {
                        return fetchOverview(requestNumber).then(function (overview) {
                            configureFilters(overview);
                            return fetchStudent();
                        });
                    }
                    return fetchStudent();
                }
                if (state.page > 1 || state.year || state.simulation) {
                    return fetchOverview(requestNumber);
                }
                return result.overview;
            });
        }

        request.then(function () {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            showState('content');
            renderCurrentData();
            updateUrl(true);
            if (state.level === 'global' && state.selectedProgramId) {
                loadSelectedProgram();
            }
        }).catch(function (error) {
            if (requestNumber !== state.requestNumber) {
                return;
            }
            if (state.level === 'global' && !state.importId && error.status === 404) {
                showState('empty');
                return;
            }
            setText('[data-error-message]', errorMessage(error));
            showState('error');
        });
    }

    function requestCurrentData(requestNumber) {
        if (state.level === 'program') {
            return fetchProgram(requestNumber);
        }
        if (state.level === 'student') {
            return fetchStudent();
        }
        return fetchOverview(requestNumber);
    }

    function loadSelectedProgram() {
        if (!state.selectedProgramId || !state.importId) {
            state.selectedProgramRequest += 1;
            renderSelectedProgram(null);
            return;
        }
        var requestId = ++state.selectedProgramRequest;
        renderSelectedProgram(null);
        apiRequest(Object.assign({
            resource: 'program',
            import_id: state.importId,
            program_id: state.selectedProgramId,
            page: 1
        }, buildFilterParams())).then(function (program) {
            if (requestId === state.selectedProgramRequest && state.level === 'global' && state.selectedProgramId === program.program.program_id) {
                renderSelectedProgram(program);
            }
        }).catch(function (error) {
            if (requestId !== state.selectedProgramRequest) {
                return;
            }
            if (error.status !== 404) {
                setText('[data-error-message]', errorMessage(error));
            }
            renderSelectedProgram(null);
        });
    }

    function openProgram(programId) {
        window.clearTimeout(state.searchTimer);
        state.level = 'program';
        state.programId = String(programId);
        state.page = 1;
        state.studentSearch = '';
        state.studentRef = '';
        state.program = null;
        updateUrl(false);
        loadCurrentView();
    }

    function openStudent(documentNumber) {
        ++state.requestNumber;
        window.clearTimeout(state.searchTimer);
        showState('loading');
        apiRequest({ resource: 'student' }, {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                'X-Dashboard-Request': '1',
                'X-CSRF-Token': root.dataset.csrfToken
            },
            body: JSON.stringify({
                import_id: state.importId,
                document: documentNumber
            })
        }).then(function (student) {
            state.student = student;
            state.studentRef = student.student_ref;
            state.level = 'student';
            updateUrl(false);
            showState('content');
            renderCurrentData();
        }).catch(function (error) {
            setText('[data-error-message]', errorMessage(error));
            showState('error');
        });
    }

    function changeFilters() {
        state.year = yearFilter.value;
        state.simulation = simulationFilter.value;
        state.subject = subjectFilter.value;
        state.page = 1;
        updateFilterContext();
        updateUrl(true);
        if (state.level === 'student' && state.student) {
            renderStudent(state.student);
            return;
        }
        loadCurrentView();
    }

    function resetFilters() {
        state.year = '';
        state.simulation = '';
        state.subject = 'global';
        state.page = 1;
        state.studentSearch = '';
        state.selectedProgramId = '';
        if (yearFilter) { yearFilter.value = ''; }
        if (simulationFilter) { simulationFilter.value = ''; }
        if (subjectFilter) { subjectFilter.value = 'global'; }
        if (programFilter) { programFilter.value = ''; }
        var search = root.querySelector('[data-student-search]');
        if (search) { search.value = ''; }
        updateUrl(true);
        loadCurrentView();
    }

    function changeGlobalPage(delta) {
        var programs = state.overview ? state.overview.programs || [] : [];
        var totalPages = Math.max(1, Math.ceil(programs.length / PROGRAMS_PER_PAGE));
        var nextPage = state.page + delta;
        if (nextPage < 1 || nextPage > totalPages) {
            return;
        }
        state.page = nextPage;
        updateUrl(true);
        renderOverview(state.overview, false);
    }

    function changeStudentPage(delta) {
        var totalPages = state.program ? state.program.total_pages : 1;
        var nextPage = state.page + delta;
        if (nextPage < 1 || nextPage > totalPages) {
            return;
        }
        state.page = nextPage;
        updateUrl(true);
        loadProgramStudents();
    }

    function loadProgramStudents() {
        window.clearTimeout(state.searchTimer);
        var requestNumber = ++state.requestNumber;
        var status = root.querySelector('[data-student-search-status]');
        status.textContent = state.studentSearch ? 'Buscando…' : 'Cargando resultados…';
        fetchProgram(requestNumber).then(function (program) {
            if (requestNumber !== state.requestNumber || state.level !== 'program') {
                return;
            }
            renderProgramStudents(program);
            status.textContent = state.studentSearch ? 'Búsqueda activa' : '';
            updateUrl(true);
        }).catch(function (error) {
            if (requestNumber !== state.requestNumber || state.level !== 'program') {
                return;
            }
            status.textContent = errorMessage(error);
        });
    }

    yearFilter.addEventListener('change', changeFilters);
    simulationFilter.addEventListener('change', changeFilters);
    subjectFilter.addEventListener('change', function () {
        state.subject = subjectFilter.value;
        updateFilterContext();
        updateUrl(true);
        renderCurrentData();
        if (state.level === 'global' && state.selectedProgramId) {
            loadSelectedProgram();
        }
    });
    root.querySelector('[data-reset-filters]').addEventListener('click', resetFilters);
    root.querySelector('[data-retry-dashboard]').addEventListener('click', loadCurrentView);
    root.querySelector('[data-program-prev]').addEventListener('click', function () { changeGlobalPage(-1); });
    root.querySelector('[data-program-next]').addEventListener('click', function () { changeGlobalPage(1); });
    root.querySelector('[data-student-prev]').addEventListener('click', function () { changeStudentPage(-1); });
    root.querySelector('[data-student-next]').addEventListener('click', function () { changeStudentPage(1); });
    programFilter.addEventListener('change', function () {
        state.selectedProgramId = programFilter.value;
        updateUrl(true);
        if (state.selectedProgramId) {
            loadSelectedProgram();
        } else {
            renderSelectedProgram(null);
        }
    });

    var studentSearch = root.querySelector('[data-student-search]');
    studentSearch.addEventListener('input', function () {
        state.studentSearch = studentSearch.value.trim();
        state.page = 1;
        ++state.requestNumber;
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(function () {
            loadProgramStudents();
        }, 300);
    });

    window.addEventListener('popstate', function () {
        readUrlState();
        loadCurrentView();
    });

    readUrlState();
    studentSearch.value = state.studentSearch;
    loadCurrentView();
}());
