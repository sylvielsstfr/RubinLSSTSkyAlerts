import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from astropy.time import Time
from astropy.coordinates import EarthLocation, get_sun
import astropy.units as u

# 1. Configuration du site : Cerro Pachón (LSST)
lsst_site = EarthLocation(lat=-30.2446*u.deg, lon=-70.7494*u.deg, height=2663*u.m)

# 2. Définition de la plage de dates
start_date = "2025-04-01"
end_date = "2026-04-01"

t_start = Time(f"{start_date} 12:00:00") # On part de midi pour trouver le minuit suivant
t_end = Time(f"{end_date} 12:00:00")
t_days = Time(np.arange(t_start.mjd, t_end.mjd, 1), format='mjd')

# 3. Calcul du vrai minuit local (Solaire)
lst_at_solar_midnight = []
true_midnight_times = []

for t in t_days:
    # On cherche le moment où le soleil est à l'anti-méridien (Apparent Anti-Solar Time)
    # Pour faire simple et précis, on calcule le LST quand le Soleil est à RA + 12h
    sun_coords = get_sun(t)
    # Le minuit local (vrai) se produit quand LST = RA_sun + 12h (soit 180°)
    solar_midnight_lst = (sun_coords.ra.deg + 180) % 360
    lst_at_solar_midnight.append(solar_midnight_lst)
    true_midnight_times.append(t.datetime)

lst_at_solar_midnight = np.array(lst_at_solar_midnight)

# --- Gestion du saut 360 -> 0 pour le plot ---
diff = np.diff(lst_at_solar_midnight)
break_indices = np.where(np.abs(diff) > 300)[0]

plot_dates = np.array(true_midnight_times)
plot_lst = lst_at_solar_midnight.copy()

for idx in reversed(break_indices):
    plot_dates = np.insert(plot_dates, idx + 1, np.datetime64('nat'))
    plot_lst = np.insert(plot_lst, idx + 1, np.nan)

# 4. Création du plot
fig, ax1 = plt.subplots(figsize=(12, 7))

ax1.plot(plot_dates, plot_lst, color='indigo', lw=2.5, label='RA au zénith à minuit vrai')

ax1.set_xlabel('Date (Calendrier)')
ax1.set_ylabel('Ascension Droite [degrés]')
ax1.set_ylim(0, 360)
ax1.set_yticks(np.arange(0, 361, 45))
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.set_title(f'RA au Méridien au Minuit Solaire Local - LSST\n({start_date} au {end_date})')

# Formatage axes
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.setp(ax1.get_xticklabels(), rotation=30, ha='right')

ax2 = ax1.twiny()
ax2.set_xlim(ax1.get_xlim())
xticks_loc = ax1.get_xticks()
mjd_labels = [Time(mdates.num2date(x)).mjd for x in xticks_loc]
ax2.set_xticks(xticks_loc)
ax2.set_xticklabels([f"{m:.0f}" for m in mjd_labels])
ax2.set_xlabel('Modified Julian Date (MJD)')

plt.tight_layout()
plt.show()


