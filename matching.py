"""
Sistema de matching - calcula a compatibilidade entre as preferências do usuário e as características dos pets, gerando um percentual de match e logs explicativos para cada critério avaliado.
"""

NIVEIS_ENERGIA = {'baixa': 0, 'media': 1, 'alta': 2}
NIVEIS_PORTE = {'pequeno': 0, 'medio': 1, 'grande': 2}
NIVEIS_TEMPO_AUSENTE = {'pouco': 0, 'medio': 1, 'muito': 2}
NIVEIS_TOLERANCIA = {'baixa': 0, 'media': 1, 'alta': 2}
NIVEIS_INDEPENDENCIA = {'baixa': 0, 'media': 1, 'alta': 2}

PESOS = {
    'tempo_ausente': 4,
    'energia': 4,
    'outros_pets': 5,
    'moradia': 2,
    'tolerancia': 2,
    'porte': 1,
}


def score_proximidade(pref_valor, pet_valor, niveis, peso_maximo):
    if not pref_valor or pref_valor in ('', 'indiferente'):
        return 0, 0
    pref_nivel = niveis.get(pref_valor, 1)
    pet_nivel = niveis.get(pet_valor, 1)
    diferenca = abs(pref_nivel - pet_nivel)
    if diferenca == 0:
        return peso_maximo, peso_maximo
    elif diferenca == 1:
        return peso_maximo * 0.6, peso_maximo
    else:
        return 0, peso_maximo


def calcular_match_completo(prefs, pet):
    score_obtido = 0
    score_maximo = 0
    bonus_pontos = 0
    penalidade_total = 0
    logs = []
    alertas = []
    informativos = []
    incompatibilidade_critica = False

    # 1. CRIANÇAS (hard rule)
    tem_criancas = prefs.get('criancas') == 'sim'
    if tem_criancas and not pet.aceita_criancas:
        incompatibilidade_critica = True
        alertas.insert(0, "❌ Pet NÃO aceita crianças (incompatibilidade grave)")

    # 2. TEMPO AUSENTE + INDEPENDÊNCIA
    tempo_ausente = prefs.get('tempo_ausente')
    if tempo_ausente and tempo_ausente != '':
        independencia_pet = getattr(pet, 'independencia', 'media')
        obtido, maximo = score_proximidade(tempo_ausente, independencia_pet,
                                           NIVEIS_INDEPENDENCIA, PESOS['tempo_ausente'])
        score_obtido += obtido
        score_maximo += maximo

        eh_apegado = independencia_pet == 'baixa'
        tempo_muito = tempo_ausente == 'muito'

        if obtido == PESOS['tempo_ausente']:
            if not (tempo_muito and eh_apegado):
                logs.append("✓ Pet se adapta bem ao seu tempo disponível")
        elif obtido > 0 and tempo_muito:
            alertas.append("⚠️ Você fica muito tempo fora – verifique se o pet se adapta")

        if tempo_muito:
            if independencia_pet == 'alta':
                bonus_pontos += 2
                logs.append("🏆 Pet independente – ótimo para sua rotina")
            elif eh_apegado:
                penalidade_total += 3
                alertas.append("⚠️ Pet muito apegado – pode sofrer com sua ausência")
        elif tempo_ausente == 'pouco' and eh_apegado:
            bonus_pontos += 1

    # 3. ENERGIA
    energia_pref = prefs.get('energia')
    energia_pet = pet.energia.lower() if pet.energia else 'media'
    obtido, maximo = score_proximidade(energia_pref, energia_pet, NIVEIS_ENERGIA, PESOS['energia'])
    score_obtido += obtido
    score_maximo += maximo
    if obtido == PESOS['energia']:
        logs.append("✓ Energia compatível com seu estilo de vida")
    elif obtido > 0:
        logs.append("✓ Energia razoavelmente compatível")

    # 4. PORTE
    porte_pref = prefs.get('porte')
    porte_pet = pet.porte.lower() if pet.porte else ''
    if porte_pref and porte_pref not in ('', 'indiferente'):
        if porte_pref == porte_pet:
            score_obtido += PESOS['porte']
            logs.append(f"✓ Porte {porte_pet} é o que você busca")
        else:
            logs.append(f"ℹ️ Porte {porte_pet} não é sua preferência")
        score_maximo += PESOS['porte']

    # 5. MORADIA (com penalidade extra)
    moradia = prefs.get('moradia')
    if moradia:
        pontos_porte = 0
        pontos_energia = 0

        if porte_pet == 'pequeno':
            pontos_porte = 1
        elif porte_pet == 'medio':
            pontos_porte = 0.5
        else:
            pontos_porte = 0

        if energia_pet == 'baixa':
            pontos_energia = 1
        elif energia_pet == 'media':
            pontos_energia = 0.5
        else:
            pontos_energia = 0

        pontos_total = pontos_porte + pontos_energia
        score_obtido += pontos_total
        score_maximo += PESOS['moradia']

        if moradia == 'casa_quintal':
            logs.append("✓ Casa com quintal – espaço ideal")
        elif moradia == 'casa_sem_quintal':
            if pontos_total >= 1.5:
                logs.append("✓ Casa sem quintal adequada para este pet")
            elif pontos_total >= 1:
                logs.append("ℹ️ Casa sem quintal pode funcionar")
            else:
                alertas.append("⚠️ Pet de grande porte e/ou alta energia pode precisar de mais espaço")
        elif moradia == 'apartamento':
            if pontos_total >= 1.5:
                logs.append("✓ Apartamento adequado para este pet")
            elif pontos_total >= 1:
                logs.append("ℹ️ Apartamento pode funcionar")
            else:
                alertas.append("⚠️ Pet de grande porte e/ou alta energia em apartamento é desafiador")
                penalidade_total += 3

    # 6. TOLERÂNCIA (vocalização)
    tolerancia_pref = prefs.get('tolerancia')
    vocalizacao = getattr(pet, 'vocalizacao', 'media')
    obtido, maximo = score_proximidade(tolerancia_pref, vocalizacao, NIVEIS_TOLERANCIA, PESOS['tolerancia'])
    score_obtido += obtido
    score_maximo += maximo
    if vocalizacao == 'alta' and tolerancia_pref == 'baixa':
        alertas.append("⚠️ Pet vocaliza muito – considere sua tolerância")
    elif obtido == PESOS['tolerancia']:
        logs.append("✓ Tolerância compatível")

    # 7. OUTROS PETS (com mensagem específica por espécie)
    outros_pets = prefs.get('outros_pets')
    if outros_pets and outros_pets != 'nao':
        score_maximo += PESOS['outros_pets']
        ok = False
        pet_especie = pet.especie.lower() if pet.especie else ''
        
        if outros_pets == 'cao':
            ok = getattr(pet, 'aceita_caes', True)
            if ok:
                if pet_especie == 'gato':
                    logs.append("✓ Gato aceita a presença de cães")
                else:
                    logs.append("✓ Convive bem com outros cães")
        elif outros_pets == 'gato':
            ok = getattr(pet, 'aceita_gatos', True)
            if ok:
                if pet_especie == 'cao':
                    logs.append("✓ Cachorro aceita a presença de gatos")
                else:
                    logs.append("✓ Convive bem com outros gatos")
        elif outros_pets == 'ambos':
            ok = getattr(pet, 'aceita_caes', True) and getattr(pet, 'aceita_gatos', True)
            if ok:
                logs.append("✓ Aceita a convivência com cães e gatos")
        
        if ok:
            score_obtido += PESOS['outros_pets']
        else:
            penalidade_total += 2
            alertas.append("⚠️ Pet pode não aceitar seus outros animais")

    # BÔNUS DIRETOS
    idade_pref = prefs.get('idade_preferida')
    idade_meses = pet.idade_meses
    if idade_pref and idade_pref not in ('', 'indiferente'):
        if (idade_pref == 'filhote' and idade_meses <= 12) or \
           (idade_pref == 'adulto' and 12 < idade_meses <= 84) or \
           (idade_pref == 'senior' and idade_meses > 84):
            bonus_pontos += 1
            logs.append("✓ Idade compatível")

    if prefs.get('castrado') == 'sim' and pet.castrado:
        bonus_pontos += 1
        logs.append("✓ Pet castrado")

    sexo_pref = prefs.get('sexo')
    sexo_pet = pet.sexo.lower() if pet.sexo else ''
    if sexo_pref and sexo_pref not in ('', 'indiferente') and sexo_pet:
        if sexo_pref == sexo_pet:
            bonus_pontos += 1
            logs.append("✓ Sexo compatível")

    # COMPLETUDE
    criterios_principais = ['energia', 'tempo_ausente', 'moradia', 'tolerancia', 'porte']
    criterios_respondidos = sum(1 for c in criterios_principais
                                if prefs.get(c) and prefs.get(c) not in ('', 'indiferente'))
    completude = int((criterios_respondidos / len(criterios_principais)) * 100)

    # INFORMAÇÕES ADICIONAIS
    if pet.castrado:
        informativos.append("📌 Pet já castrado")
    else:
        informativos.append("📌 Pet não é castrado")
    if pet.vacinado:
        informativos.append("📌 Vacinas em dia")
    if getattr(pet, 'necessidades_especiais', False) and not incompatibilidade_critica:
        informativos.append("📌 Pet possui necessidades especiais – requer cuidados extras")

    if alertas:
        logs_alerta = ["⚠️ PONTOS DE ATENÇÃO:"]
        logs_alerta.extend(alertas)
        logs_alerta.append("")
        logs = logs_alerta + logs
    if informativos:
        logs.append("")
        logs.append("📋 INFORMAÇÕES SOBRE O PET:")
        logs.extend(informativos)

    if incompatibilidade_critica:
        return 0, logs, completude

    if score_maximo == 0:
        return 50, ["ℹ️ Responda mais perguntas para melhorar a precisão da recomendação"], completude

    percentual_base = (score_obtido / score_maximo) * 100
    percentual_final = percentual_base + bonus_pontos - penalidade_total

    percentual_final = max(0, min(100, percentual_final))

    return int(percentual_final), logs, completude


def filtrar_por_especie(prefs, pets):
    especie = prefs.get('especie')
    if especie == 'ambos':
        return pets
    return [p for p in pets if p.especie.lower() == especie.lower()]


def get_pets_recomendados(prefs, todos_pets):
    filtrados = filtrar_por_especie(prefs, todos_pets)
    resultados = []
    for pet in filtrados:
        percentual, logs, completude = calcular_match_completo(prefs, pet)
        resultados.append({
            'pet': pet,
            'percentual': percentual,
            'completude': completude,
            'logs': logs
        })
    resultados.sort(key=lambda x: x['percentual'], reverse=True)
    return resultados


def formatar_recomendacao(resultado):
    pet = resultado['pet']
    pct = resultado['percentual']
    completude = resultado['completude']
    logs = resultado['logs']

    if pct >= 90:
        classe = "super-match"
        texto = "Match Excelente"
    elif pct >= 75:
        classe = "alta-match"
        texto = "Alta Compatibilidade"
    elif pct >= 60:
        classe = "bom-match"
        texto = "Boa Compatibilidade"
    elif pct >= 40:
        classe = "medio-match"
        texto = "Compatibilidade Média"
    else:
        classe = "baixo-match"
        texto = "Compatibilidade Baixa"

    if pct >= 90:
        frase = "🏆 Excelente opção para seu perfil!"
    elif pct >= 75:
        frase = "🎯 Ótima compatibilidade com seu perfil!"
    elif pct >= 60:
        frase = "✅ Se adapta bem ao seu estilo de vida."
    elif pct >= 40:
        frase = "📌 Pode funcionar com algumas adaptações."
    else:
        frase = "⚠️ Verifique os pontos de atenção."

    return {
        'pet': pet,
        'percentual': pct,
        'completude': completude,
        'classe_css': classe,
        'texto_match': texto,
        'frase_personalizada': frase,
        'logs': logs
    }