
import csv

###############################
########### Traitement des fichiers CSV de base
# mise en majuscule des nom et prénom, suppression des accents
# comparaison nom_prenom et prenom_nom 

def memes_lettres (ch1, ch2) :
    """compare si deux chaine possède les mêmes lettres"""
    if len(ch1) != len(ch2) :
        return False
    dic1 = dict()
    dic2 = dict()
    for i in ch1 :
        if i in dic1 :
            dic1[i] = dic1[i] + 1
        else :
            dic1[i] = 1
    for i in ch2 :
        if i in dic2 :
            dic2[i] = dic2[i] + 1
        else :
            dic2[i] = 1
    return dic1 == dic2

def cle_presente (dic, ch) :
    """compare cle d'un dictionnaire avec une chaine"""
    for j in dic :
        if memes_lettres(j, ch) : # signifie que 'ch' est déjà présent dans dic
            return True
    return False

def invers_cle(ch) :
    """inverse une cle du type 'ch1_ch2' en 'ch2_ch1'."""
    ch1 = ""
    ch2 = ""
    i = 0
    while ch[i] != '_' :
        ch1 = ch1 + ch[i]
        i += 1
    for j in range (i+1, len(ch)) :
        ch2 = ch2 + ch[j]
    return ch2+'_'+ch1

def supprime_accent (chaine) :
    """supprime les accents de la chaine et les remplace par des lettres non accentuées"""
    accents = { 'a' :  ['à', 'ã', 'á', 'â','Ã¢'], \
                'e': ['é', 'è', 'ê', 'ë', 'Ã©','Ã¨', 'Ã‰','Ã«'], \
                'i': ['î', 'ï', 'Ã¯'], \
                'u': ['ù', 'ü', 'û'], \
                'o': ['ô', 'ö'] }
    for char , accents_chars in accents.items() :
        for accent_char in accents_chars :
            chaine = chaine.replace(accent_char, char)
    return chaine

def valide (x) :#crée une copie de la table en modifiant le type de certaines données
    characters = " "
    firstname = supprime_accent(x["firstname"]) # supprime les accents du firstname
    firstname = firstname.upper()               # passe en majuscule le firstname
    firstname = "".join( x for x in firstname if x not in characters) # retire les espasces du firstname
    lastname = supprime_accent(x["lastname"])   # idem pour lastaname
    lastname = lastname.upper()                 # idem pour lastaname
    lastname = "".join( x for x in lastname if x not in characters) # idem pour lastaname
    firstname_lastname = firstname + '_' + lastname # créer une clé composée de firstname_lastname
    club  =  (x["club"])
    sex  = (x["sex"])
    category = (x["category"])
    rank = (x["rank"])
    if int(x["rank"]) <= 30 : # ajout de la catégorie points
        points = 31 - int(x["rank"])
    else :
        points = 0
    return {"firstname_lastname": firstname_lastname, \
            "club" : club, "sex" : sex, "category" : category,\
            "points" : points}


###################################

#### créer les tables par catégorie et sexe / appel à chaque compet
def tab_c0_sF(tab) : # créer table cat 0 Fille / senior fille
    return [e for e in tab if e['category'] == '0' and e['sex'] == 'F']

def tab_c1_sF(tab) :# créer table cat 1 Fille / titane fille
    return [e for e in tab if e['category'] == '1' and e['sex'] == 'F']

def tab_c2_sF(tab) :# créer table cat 1 Fille / diamant fille
    return [e for e in tab if e['category'] == '2' and e['sex'] == 'F']

def tab_c0_sM(tab) :# créer table cat 0 Garçon / senior homme
    return [e for e in tab if e['category'] == '0' and e['sex'] == 'M']

def tab_c1_sM(tab) :# créer table cat 1 Garçons / titane homme
    return [e for e in tab if e['category'] == '1' and e['sex'] == 'M']

def tab_c2_sM(tab) :# créer table cat 1 Garçons / diamant homme
    return [e for e in tab if e['category'] == '2' and e['sex'] == 'M']



# fichier des compétitions sous forme de liste
# contient le nom des fichiers des compet
tab = ["competitionresults_RSCC_anon.csv",
       "competitionresults_ESC15_anon.csv"]
n = len(tab) # connnaitre le nombre de compet
i = 0 # numero de la table
# i sera le repére des compet
# une table par catégorie
tab_cat_0_sex_F = [0]*n
tab_cat_1_sex_F = [0]*n
tab_cat_2_sex_F = [0]*n
tab_cat_0_sex_M = [0]*n
tab_cat_1_sex_M = [0]*n
tab_cat_2_sex_M = [0]*n
# boucle pour l'ouverture des fichiers
for j in tab : # parcours l'ensemble des fichiers des compétitions et les prend un par un
    fichier = open (j)  # ouverture du fichier sélectionner/pris
    dict_results = list(csv.DictReader(fichier, delimiter=",")) # conversion en dictionnaire avec séparateur virgule

    # creation de la nouvelle table avec fistname lastnane club sex category rank et points au nouveau format
    # "firstname_lastname": firstname_lastname, "club" : club, "sex" : sex, "category" : category,"points" : points
    dict_results_val = [valide(x) for x in dict_results]
    
    tab_cat_0_sex_F[i] = tab_c0_sF(dict_results_val) # sélectionne dans la table valide uniquement les filles de cat 0/sénior
    
    tab_cat_1_sex_F[i] = tab_c1_sF(dict_results_val) # sélectionne dans la table valide uniquement les filles de cat 1/titane

    tab_cat_2_sex_F[i] = tab_c2_sF(dict_results_val) # sélectionne dans la table valide uniquement les filles de cat 2/diamant

    tab_cat_0_sex_M[i] = tab_c0_sM(dict_results_val) # sélectionne dans la table valide uniquement les garçons de cat 0/sénior

    tab_cat_1_sex_M[i] = tab_c1_sM(dict_results_val) # sélectionne dans la table valide uniquement les garçons de cat 1/titane

    tab_cat_2_sex_M[i] = tab_c2_sM(dict_results_val) # sélectionne dans la table valide uniquement les garçons de cat 2/diamant
    
    i += 1
    # au terme de cette boucle, on a 6 tables de 'n' tables (catégorie et sexe) pour chacune des 'n' compétitions
    # exemple : la table 'tab_cat_0_sex_F = [[table de la compet 0],[table de la compet 1],[table de la compet 2],[table de la compet 3],...]

#for i in range (len(tab_cat_1_sex_M)) : 
    #print(tab_cat_1_sex_M[i])
########################################
### partie création de nouveau dictionnaire avec :
    # ajout d'un tableau (avec nouvelle clé 'tab_points') des points obtenu lors des contests
    # cummul des points sous nouvelle clé 'score'

def dict_destab(tab) : # retourne un dictionnaire avec le cumul des points de toutes les compéttions
    score = dict()
    number_double = 0 # variable si on tombe sur des personne portant le même nom
    for i in range (len(tab)) : # parcours des éléments du tab, chaque élément est une compet
        for j in tab[i] : #parcours chaque élémént d'une compet
            if cle_presente(score,j["firstname_lastname"]) : # si cle (composée de nom_et_prénom) est dans dict
                if j["firstname_lastname"] in score : # dans le bon ordre, on ajoute les points
                    score[j["firstname_lastname"]]["tab_points"].append(j["points"]) # ajout des points
                else : # si cle (composée de nom_et_prénom) est dans dict, mais pas dans le bon ordre -> inversion de la clé et ajout des points 
                    ch = invers_cle(j["firstname_lastname"])
                    score[ch]["tab_points"].append(j["points"])
            else : # sinon, si clé pas présente (première fois rencontrer) , ajout de la clé et de son premier score
                score[j["firstname_lastname"]] = j # ajout de la clé dans dictionnaire : cle = firstname_lastname
                #print(score)
                #print(score[j["firstname_lastname"]])
                score[j["firstname_lastname"]]["tab_points"]=[score[j["firstname_lastname"]]["points"]] # ajout de la valeur à la clé
    return(score) # renvoie dictionnaire score

def dict_destab_nb_participation(dic_tab,n) :
    """ reçoit le tab avec dic et tab des points par compet
        et n le nombre de compet
        renvoie dictionnaire ajouter du score"""
    for i in dic_tab :
        nb_part = len(dic_tab[i]["tab_points"]) # calcul le nombre de participation du compétiteur
        if nb_part <= n : # si a fait moins de contest que nombre total de contest ### nb_part < n : à la base pour n compet - 1
            dic_tab[i]["score"] = sum(dic_tab[i]["tab_points"]) # ajoute la somme de ses points
        else : # sinon
            dic_tab[i]["score"] = sum(dic_tab[i]["tab_points"]) - min(dic_tab[i]["tab_points"]) #ajoute la somme de ses pts moins le plus mauvais de ses résultat
    return dic_tab    
       
######################################
### Partie classemment

def val_points(x) : # permet le classement en ordre croisssant
    return x['score']

def score_classe(dic) : # A partir du dictionnaire , crée une liste classé
    score_list = []
    for key, value in dic.items():
        score_list.append(value)
    return(sorted(score_list, key = val_points, reverse = True))

######################################
### partie création des fichier CSV

def fichier_csv (tab_classement) : # génére fichiers csv
    cat = ["senior femme", "titane femme", "diamant femmme",\
           "senior homme", "titane homme", "diamant homme"]
    i = 0
    for j in tab_classement :
        sortie = open("Classement "+cat[i]+".csv", "w")
        writer = csv.DictWriter(sortie, fieldnames = ['firstname_lastname', 'club', 'sex', 'category', 'tab_points','score', 'rang'])
        writer.writeheader()
        writer.writerows(j)
        sortie.close()
        i += 1
#####################################
#### partie nombre de participants et proportionnalité
        
def nombre_participant_f_h (tab_classement) :
    nb_f = 0
    nb_h = 0
    for i in range (0, 3) :
        nb_f = nb_f + len(tab_classement[i])
    for i in range (3, 6) :
        nb_h = nb_h + len(tab_classement[i])
    proportion_f = nb_f / (nb_f + nb_h)
    proportion_h = nb_h / (nb_f + nb_h)
    return [{'Nombre de Femmes' : nb_f,'Nombre de Hommes' : nb_h,\
            'Proportion F' : proportion_f*100, 'Proportion H' : proportion_h*100}]

def fichier_csv_propor (chiffres) : # génére fichiers csv sur les proportionnalite
    sortie = open("01 Proportion.csv", "w")
    writer = csv.DictWriter(sortie, fieldnames = ['Nombre de Femmes','Nombre de Hommes','Proportion F','Proportion H'])
    writer.writeheader()
    writer.writerows(chiffres)
    sortie.close()

#####################################
##### partie ajout du rang 1er 2eme 3mem etc ....


def ajout_rang(x) :
    tab = []
    rang = 1
    for i in x : 
        firstname_lastname = i["firstname_lastname"]
        club = i["club"]
        sex  = (i["sex"])
        category = (i["category"])
        tab_points = (i["tab_points"])
        score = i["score"]
        rang = rang
        tab.append({"firstname_lastname": firstname_lastname, \
            "club" : club, "sex" : sex, "category" : category,\
            "tab_points" : tab_points, "score" : score, "rang" : rang})
        rang += 1
    return tab

def verifi_rang(tab) :
    for i in range (len(tab)-1) :
        if tab[i]["score"] == tab[i+1]["score"] :
            ancien_rang = tab[i]["rang"]
            tab[i+1]["rang"] = ancien_rang
    return tab




### programme principal ###
#print("    ####    programme principal     ####     ")
# filles séniors
score_cat_0_sex_F = score_classe(dict_destab_nb_participation(dict_destab(tab_cat_0_sex_F),n))
                                                             # création dict avec cumul de tous les points dans table obtenu par compet
                                #renvoie dict avec cumul des points et nouveau paramètre le score total
                    # créer la liste classé
score_cat_0_sex_F_rang = ajout_rang(score_cat_0_sex_F)
score_cat_0_sex_F_rang_verif = verifi_rang(score_cat_0_sex_F_rang)

#filles titanes
score_cat_1_sex_F = score_classe(dict_destab_nb_participation(dict_destab(tab_cat_1_sex_F),n))
score_cat_1_sex_F_rang = ajout_rang(score_cat_1_sex_F) # ajout du rang
score_cat_1_sex_F_rang_verif = verifi_rang(score_cat_1_sex_F_rang)

# filles diamants
score_cat_2_sex_F = score_classe(dict_destab_nb_participation(dict_destab(tab_cat_2_sex_F),n))
score_cat_2_sex_F_rang = ajout_rang(score_cat_2_sex_F)
score_cat_2_sex_F_rang_verif = verifi_rang(score_cat_2_sex_F_rang)

# garçons séniors
score_cat_0_sex_M = score_classe(dict_destab_nb_participation(dict_destab(tab_cat_0_sex_M),n))
score_cat_0_sex_M_rang = ajout_rang(score_cat_0_sex_M)
score_cat_0_sex_M_rang_verif = verifi_rang(score_cat_0_sex_M_rang)

# garçons titanes
score_cat_1_sex_M = score_classe(dict_destab_nb_participation(dict_destab(tab_cat_1_sex_M),n))
score_cat_1_sex_M_rang = ajout_rang(score_cat_1_sex_M)
score_cat_1_sex_M_rang_verif = verifi_rang(score_cat_1_sex_M_rang)

# garçons diamants
score_cat_2_sex_M = score_classe(dict_destab_nb_participation(dict_destab(tab_cat_2_sex_M),n))
score_cat_2_sex_M_rang = ajout_rang(score_cat_2_sex_M) # ajout du rang
score_cat_2_sex_M_rang_verif = verifi_rang(score_cat_2_sex_M_rang)# verif rang si égalité de score


tab_classement = [score_cat_0_sex_F_rang_verif,\
                  score_cat_1_sex_F_rang_verif,\
                  score_cat_2_sex_F_rang_verif,\
                  score_cat_0_sex_M_rang_verif,\
                  score_cat_1_sex_M_rang_verif,\
                  score_cat_2_sex_M_rang_verif]

print (score_cat_1_sex_F_rang_verif)
chiffres = nombre_participant_f_h (tab_classement)



fichier_csv (tab_classement)
fichier_csv_propor(chiffres)
