import matplotlib.pyplot as plt
import numpy as np

# Générer des valeurs de x
x = np.linspace(-10, 10, 400)

# Calculer les valeurs de y = asinh(x)
y = np.arcsinh(x)

# Calculer les valeurs de y = ln(x)
y_ln = np.log(x)

# Calculer les magnitudes
y_mag = 2.5 * np.log10(x)


# Tracer la courbe
plt.figure(figsize=(8, 6))
plt.plot(x, y, label="y = asinh(x)", color="b")
plt.plot(x, y_ln, label="y = ln(x)", color="r")
plt.plot(x, y_mag, label="y = 2.5*log(x)", color="g")

plt.title("Courbe de la fonction y = asinh(x)")
plt.xlabel("x")
plt.ylabel("y")
plt.grid(True)
plt.legend()
plt.axhline(0, color="black", linewidth=0.5)
plt.axvline(0, color="black", linewidth=0.5)
plt.show()
