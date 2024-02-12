
import csv

###############################
########### Traitement des fichiers CSV de base


# valide table


def valide (x) :#crée une copie de la table en modifiant le type de certaines données
    firstname_lastname = x["firstname_lastname"]
    club  =  (x["club"])
    sex  = (x["sex"])
    category = int(x["category"])
    tab_points = (x["tab_points"])
    score = int(x["score"])
    rang = int(x["rang"])

    return {"firstname_lastname": firstname_lastname, \
            "club" : club, "sex" : sex, "category" : category,\
            "tab_points" : tab_points , "score" : score, "rang" : rang}

########################################
######## partie création dictionnaire avec :
    #### clé  : club
    #### valeur : tableau des rank

def dic_club_rangs (tab) :
    """renvoie un dictionnaire avec pour clé le nom des club
     et pour valeur un tableau avec les différents rank"""
    tab_club_rangs = dict()
    for k in tab :
        for i in k :
            if i['club'] in tab_club_rangs :
                tab_club_rangs[i['club']].append(i['rang'])
            else :
                tab_club_rangs[i['club']] = [i['rang']]
    return tab_club_rangs #########focntionne

######################################
#####  partie comptage des points

###############A revoir  !!!!!!!!!!!!!!!!!!!!!!!!!!
def comptage (dic_des_rank) :
    """ à partir d'un dict {clé=club : valeur = tab des rank}
        renvoie un dict{ clé=club : valeur = points}"""
    dic_des_points = dict()
    for key, value in dic_des_rank.items() :
        
        points  = 0 # comptage des points
        points = len(value)
        for i in value :
            if int(i) < 6 :
                points = points + (6 - int(i))
                
        if key in dic_des_points : # insertion des points
            dic_des_points[key] = dic_des_points[key] + points
        else :
            dic_des_points[key] = points
            
    return dic_des_points

#####################################
### Partie classemment

def val_points(x) : # permet le classement en ordre croisssant
    return x['points']

def score_classe(dic) : # A partir du dictionnaire , crée une liste classé
    score_list = []
    for key, value in dic.items():
        score_list.append({'club' : key , 'points' : value})
    print(score_list)
    return(sorted(score_list, key = val_points, reverse = True))

#####################################
##### partie ajout du rang 1er 2eme 3mem etc ....


def ajout_rang(x) :
    """ajoute un champs rang"""
    tab = []
    rang = 1
    for i in x : 
        club = i["club"]
        points = (i["points"])
        rang = rang
        tab.append({"club" : club, "points" : points, "rang" : rang})
        rang += 1
    return tab

def verifi_rang(tab) :
    """verifie le champs rang, si deux deuxième à égalité etc."""
    for i in range (len(tab)-1) :
        if tab[i]["points"] == tab[i+1]["points"] :
            ancien_rang = tab[i]["rang"]
            tab[i+1]["rang"] = ancien_rang
    return tab

######################################
### partie création des fichier CSV

def fichier_csv (tab_classement) : # génére fichiers csv
    sortie = open("Classement_club.csv", "w")
    writer = csv.DictWriter(sortie, fieldnames = ['club', 'points', 'rang'])
    writer.writeheader()
    writer.writerows(tab_classement)
    sortie.close()

### programme principal ###
#print("    ####    programme principal     ####     ")

# contient le nom des fichiers des classement
tab = ["Classement diamant femmme.csv","Classement diamant homme.csv",\
          "Classement senior femme.csv","Classement senior homme.csv",\
          "Classement titane femme.csv","Classement titane homme.csv"]
n = len(tab)

tab_complet = []
for i in tab :
    fichier = open (i)
    tab_dict = list(csv.DictReader(fichier, delimiter=","))
    tab_dict_val = [valide(i) for i in tab_dict]
    tab_complet.append(tab_dict_val)

dic_des_rank = dic_club_rangs (tab_complet) # dict {clé=club : valeur = tab des rank} toutes catégories , tout les compétiteurs

dictionnaire_des_points = comptage (dic_des_rank) #dict{ clé=club : valeur = points} points = cummul des participants plus bonus par les premiers

t_d_p = score_classe(dictionnaire_des_points)
t_d_p_rangs = ajout_rang(t_d_p)
t_d_p_rangs_verif = verifi_rang(t_d_p_rangs)

fichier_csv (t_d_p_rangs_verif)
print("coucou")

# reste à ajouter rang !!!!!
