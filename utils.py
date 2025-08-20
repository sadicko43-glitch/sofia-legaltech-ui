def calcular_vacaciones(anios):
    if anios == 1:
        return 12
    elif anios == 2:
        return 14
    elif anios == 3:
        return 16
    elif anios == 4:
        return 18
    elif anios >= 5:
        return 20
    else:
        return 0
