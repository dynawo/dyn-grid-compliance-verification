
# Common acronyms

BT - Basse Tension, U < 1kV

HTA - Haute Tension A, 1kV < U <= 50 kV

HTB - Haute Tension B, 50kV < U:
  * HTB1: 63 kV and 90 kV
  * HTB2: 150 kV and 225 kV
  * HTB3: 400 kV

S3REnR - Schémas régionaux de raccordement au réseau des EnR (renewables)

FCR - Frequency Containment Reserve, communément appelé réglage primaire

aFRR - Automatic Frequency Restoration Reserve, communément appelé réglage
       secondaire (AGC, automatic generation control)

LFSM - Limited Frequency Sensitive Mode, communément appelé réglage restreint à
       la sur-fréquence/à la sous-fréquence; soit par l’action manuelle des
       opérateurs assurant en permanence l’équilibrage du système électrique
       (manual Frequency Restoration Reserve (mFRR) ou Replacement Reserve (RR),
       communément appelé réglage tertiaire).




# From Chapter 2, Article 2.1 - Etudes RTE pour le raccordement

Usually new generators are assigned their connection Voltage Level according to their Pmax:

| Domaine de tension       | Pmax limite |
|--------------------------|-------------|
| HTB1 (63 kV et 90 kV)    |   50 MW     |
| HTB2 (150 kV et 225 kV)  |   250 MW    |
| HTB3 (400 kV)            |   >250 MW   |

Exceptions: Le producteur peut solliciter de RTE
  a) un raccordement en HTB1 si :  50 MW < Pmax < 100 MW
  b) un raccordement en HTB2 si : 250 MW < Pmax < 600 MW




# From Chapter 2, Article 2.2 – Schémas de raccordement

Default schemes for connection:
  1. Raccordement en antenne
  2. Raccordement en coupure (connection substation at the gen) 
  3. Raccordement en coupure (connection substation away from the gen) 

Other special schemes:
  1. "En piquage" (tapped from an existing line)
  2. Raccordement à une seule cellule disjoncteur (just one breaker)
  3. Liaison souterraine ou sous-marine de grande longueur




# From Chapter 3, Article 3.1 - Plages de tension et de fréquence normales et exceptionnelles

## Plages de tension en régime normal

En exploitation, au point de raccordement d’une installation, les plages
normales de variation de tension du réseau sont:

* de 360 à 420 kV pour le réseau 400kV (la tension nominale est de 400 kV) ==> 0,90-1,05 pu

* de 198 à 245 kV pour le réseau 225kV (la tension nominale est de 220 kV) ==> 0,90-1,118 pu

* +/- 10% de la tension contractuelle pour le réseau 150kV, sans dépasser 170 kV
  
* +/- 8 % de la tension contractuelle pour le réseau 90kV (la tension nominale
  est de 90 kV), sans dépasser 100 kV.
* +/- 8 % de la tension contractuelle pour le réseau ayant une tension nominale
  de 63, 45 et 42 kV.

Note: La tension *contractuelle* étant fixée dans une plage de +/-6% de la tension
nominale du réseau (7% for the 150kV network).


## Plages de tension en régime exceptionnel

### Plages de tension que peut atteindre le réseau 400kV
* 320-340kV  1 heure, 1 fois par an, exceptionnellement
* 340-360kV	 1 h 30, quelques fois par an
* 360-380kV	 pendant 5 heures, 10 fois par an
* 420-424kV	 pendant 20 minutes, plusieurs fois par an
* 424-428kV	 pendant 5 minutes, quelques fois par an
* 428-440kV  pendant 5 minutes, une fois tous les 10 ans

### Plages de tension que peut atteindre le réseau 225kV
* 180-190kV	   une heure, 1 fois par an, exceptionnellement
* 190-200kV	   1 h 30 quelques fois par an, exceptionnellement
* 245-247,5kV  20 minutes, quelques fois par an
* 247,5-250kV  5 minutes, exceptionnellement

### Plages de tension que peut atteindre le réseau 150V
* 170-171,5 kV     pendant 20 minutes, quelques fois par an
* 171,5-173 kV     pendant 5 minutes, exceptionnellement 
* Jusqu’à 120 kV   pendant quelques dizaines de minutes par an


## Plages de fréquence
* en régime normal: [49,95 Hz -- 50,05Hz]
* en régime exceptionnel:
    * ]47Hz ; 47,5Hz]	 pendant une minute, exceptionnellement, une fois tous les cinq à dix ans
    * ]47,5Hz ; 49Hz]	 pendant 3 minutes, exceptionnellement, une fois tous les cinq à dix ans
    * ]49Hz ; 49,5Hz]  pendant 5 heures en continu, 100 heures en durée cumulée pendant la durée de vie de l’installation
    * ]50,5Hz ; 51Hz]  pendant 1 heure en continu, 15 heures en durée cumulée pendant la durée de vie de l’installation
    * ]51Hz ; 52Hz]    pendant 15 minutes, une à cinq fois par an
    * ]52Hz ; 55Hz[    pendant 1 minute, exceptionnellement (régime transitoire)




# From Chapter 5, Article 5.1.1 - Exigences de conception et de fonctionnement pour le raccordement au RPT d’une unité de production


## Section 3: Classification of generating units

|  Generator Class  |             Criterion                 |
|-------------------|---------------------------------------|
|         A         |  0.8 kW <= Pmax < 1 MW                |
|         B         |    1 MW <= Pmax < 18 MW               |
|         C         |   18 MW <= Pmax < 75 MW               |
|         D         |   Uracc >= 110 kV and Pmax >= 0.8 kW  |
|         D         |   Uracc  < 110 kV and Pmax >= 75 kW   |

Where Uracc is the nominal voltage at the PDR bus.



## 4.4.1 Choix de la tension de dimensionnement Udim

L’article 08 de l’arrêté du 09 juin 2020 relatif aux exigences techniques
applicables aux raccordements aux réseaux publics de transport et de
distribution d’électricité, précise les limites de la plage de variation pour
fixer la valeur de Udim.

En règle générale, Udim sera choisie:
  * HTB3 (400 kV): Udim = 405 kV
  * HTB2 (225 kV): Udim = 235 kV
  * HTB1 (63 kV and 90 kV): Udim = _"tension moyenne du point de connexion"_

Des valeurs différentes sont retenues dans les cas où RTE souhaite modifier le
plan de tension de la zone et que l’installation est suffisamment puissante pour
impacter significativement la situation préexistante.



## Section 4.4.8: Tableau 10, Valeurs de réactance de liaison pour l'étude de stabilité

Les valeurs (a) et (b) de la réactance de liaison (Xcc) sont des valeurs
standards en fonction de la puissance de l’unité de production et de son niveau
de tension de raccordement:

|     Voltage levels      |    a    |                          b                                    |
|-------------------------|---------|---------------------------------------------------------------|
|          HTB1           | 0.05 pu |  if Pmax < 50 MW: 0.2 pu; if Pmax ≥ 50 MW: 0.3 pu             |
|          HTB2           | 0.05 pu |  if Pmax < 250 MW: 0.3 pu; if Pmax ≥ 250 MW: 0.54 pu          |
|          HTB3           | 0.05 pu |  if Pmax < 800 MW: 0.54 pu; if Pmax ≥ 800 MW: 0.6 pu          |
| non-synch offshore farm | 0.05 pu |  if Pmax < 50 MW: 0.2 pu; if 50 MW ≤ Pmax < 250 MW: 0.3 pu    |
| non-synch offshore farm | 0.05 pu |  if 250 MW ≤ Pmax < 800 MW: 0.54 pu; if Pmax ≥ 800 MW: 0.6 pu |

The pu base is Udim and the nominal apparent power of the generator/farm, Sn.




## Section 4.6.3: Comportement lors de court-circuits

This section defines the clearing times Tclear to be used for the simulation of
the three-phase fault used in the study of resilience against short-circuits:

"Le temps T est également un temps standard dépendant du niveau de tension:"
  * en HTB3 (400 kV): Tclear = 85 ms ;
  * en HTB2 (150 kV and 225 kV): Tclear = 85 ms ;
  * en HTB1 (63 kV and 90 kV): Tclear = 150 ms ;


