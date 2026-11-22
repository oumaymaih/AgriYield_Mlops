
/* ==========================================
   AGRIYIELD MLOPS
   Fichier : frontend/static/js/app.js
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    // ======================================
    // 1. ELEMENTS DE LA PAGE
    // ======================================

    const formIndividuel = document.getElementById("form-prediction");
    const formCSV = document.getElementById("form-csv");
    const fichierCSV = document.getElementById("fichier-csv");
    const nomFichier = document.getElementById("nom-fichier");
    const zoneImport = document.getElementById("zone-import");

    const blocResultatIndividuel = document.getElementById(
        "resultat-individuel"
    );

    const rendementPredit = document.getElementById(
        "rendement-predit"
    );

    const rendementReel = document.getElementById(
        "rendement-reel"
    );

    const blocResultatsCSV = document.getElementById(
        "resultats-csv"
    );


    // ======================================
    // 2. FONCTIONS UTILITAIRES
    // ======================================

    function afficherMessage(elementId, message, type = "info") {

        const element = document.getElementById(elementId);

        if (!element) return;

        element.textContent = message;

        element.classList.remove(
            "message-succes",
            "message-erreur",
            "message-info"
        );

        if (message) {
            element.classList.add(`message-${type}`);
        }
    }


    function extraireErreur(data) {

        if (!data) {
            return "Une erreur est survenue.";
        }

        if (typeof data.detail === "string") {
            return data.detail;
        }

        if (Array.isArray(data.detail)) {

            return data.detail.map((erreur) => {

                const champ = Array.isArray(erreur.loc)
                    ? erreur.loc.slice(1).join(".")
                    : "";

                return champ
                    ? `${champ} : ${erreur.msg}`
                    : erreur.msg;

            }).join(" ; ");
        }

        if (
            data.detail &&
            typeof data.detail === "object"
        ) {

            const detail = data.detail;

            return (
                detail.message ||
                detail.detail ||
                "Une erreur est survenue."
            );
        }

        return data.message || "Une erreur est survenue.";
    }


    async function lireReponse(reponse) {

        const texte = await reponse.text();

        let data;

        try {

            data = texte ? JSON.parse(texte) : {};

        } catch {

            throw new Error(
                `Erreur du serveur (HTTP ${reponse.status}). ` +
                "Consultez le terminal FastAPI."
            );
        }

        if (!reponse.ok) {
            throw new Error(extraireErreur(data));
        }

        return data;
    }


    function formaterRendement(valeur) {

        if (
            valeur === null ||
            valeur === undefined ||
            valeur === ""
        ) {
            return "—";
        }

        const nombre = Number(valeur);

        if (!Number.isFinite(nombre)) {
            return "—";
        }

        return nombre.toFixed(2);
    }


    // ======================================
    // 3. AFFICHAGE PREDICTION INDIVIDUELLE
    // ======================================

    function masquerResultatIndividuel() {

        if (blocResultatIndividuel) {
            blocResultatIndividuel.hidden = true;
        }

        if (rendementPredit) {
            rendementPredit.textContent = "—";
        }

        if (rendementReel) {
            rendementReel.textContent = "—";
        }
    }


    function afficherResultatIndividuel(data) {

        const prediction = data.rendement_predit;

        if (
            prediction === null ||
            prediction === undefined ||
            prediction === "" ||
            !Number.isFinite(Number(prediction))
        ) {

            throw new Error(
                "Le serveur n'a pas retourné de rendement prédit valide."
            );
        }

        if (!blocResultatIndividuel || !rendementPredit) {

            throw new Error(
                "Le bloc d'affichage du rendement est introuvable " +
                "dans prediction.html."
            );
        }

        // Afficher le rendement prédit par V1.
        rendementPredit.textContent = formaterRendement(
            prediction
        );

        // Afficher le rendement réel si disponible.
        if (rendementReel) {

            rendementReel.textContent = formaterRendement(
                data.rendement_reel
            );
        }

        // Afficher le bloc résultat.
        blocResultatIndividuel.hidden = false;
    }


    // ======================================
    // 4. PREDICTION INDIVIDUELLE
    // ======================================

    if (formIndividuel) {

        masquerResultatIndividuel();

        formIndividuel.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                masquerResultatIndividuel();

                afficherMessage(
                    "message-individuel",
                    "",
                    "info"
                );

                // ----------------------------------
                // 1. Caractéristiques du modèle V1
                // ----------------------------------

                const champs = [
                    "Crop",
                    "Season",
                    "State",
                    "Crop_Year",
                    "Area",
                    "Annual_Rainfall",
                    "Fertilizer",
                    "Pesticide"
                ];

                const donnees = {};

                let nombreManquants = 0;

                // ----------------------------------
                // 2. Récupérer les caractéristiques
                // ----------------------------------

                for (const champ of champs) {

                    const element = document.getElementById(
                        champ
                    );

                    if (!element) {

                        afficherMessage(
                            "message-individuel",
                            `Le champ ${champ} est introuvable.`,
                            "erreur"
                        );

                        return;
                    }

                    const valeur = element.value.trim();

                    if (
                        valeur === "" ||
                        ["null", "none", "nan", "na"].includes(
                            valeur.toLowerCase()
                        )
                    ) {

                        donnees[champ] = null;
                        nombreManquants++;

                    } else {

                        donnees[champ] = valeur;
                    }
                }

                // ----------------------------------
                // 3. Vérifier les valeurs manquantes
                // ----------------------------------

                if (nombreManquants > 3) {

                    afficherMessage(
                        "message-individuel",
                        `Vous avez ${nombreManquants} champs manquants. ` +
                        "Maximum autorisé : 3.",
                        "erreur"
                    );

                    return;
                }

                // ----------------------------------
                // 4. Vérifier les champs numériques
                // ----------------------------------

                const champsNumeriques = [
                    "Crop_Year",
                    "Area",
                    "Annual_Rainfall",
                    "Fertilizer",
                    "Pesticide"
                ];

                for (const champ of champsNumeriques) {

                    if (donnees[champ] === null) {
                        continue;
                    }

                    const nombre = Number(donnees[champ]);

                    if (!Number.isFinite(nombre)) {

                        afficherMessage(
                            "message-individuel",
                            `La valeur du champ ${champ} est invalide.`,
                            "erreur"
                        );

                        return;
                    }

                    if (champ === "Crop_Year") {

                        if (
                            !Number.isInteger(nombre) ||
                            nombre < 1900 ||
                            nombre > 2100
                        ) {

                            afficherMessage(
                                "message-individuel",
                                "Crop_Year doit être une année entière " +
                                "entre 1900 et 2100.",
                                "erreur"
                            );

                            return;
                        }

                    } else if (nombre < 0) {

                        afficherMessage(
                            "message-individuel",
                            `${champ} doit être positif ou nul.`,
                            "erreur"
                        );

                        return;
                    }

                    donnees[champ] = nombre;
                }

                // ----------------------------------
                // 5. Récupérer le rendement réel Yield
                // ----------------------------------

                // Yield est facultatif.
                // Il n'est pas une caractéristique du modèle.
                // Il sert uniquement à évaluer les prédictions.

                const champYield = document.getElementById(
                    "Yield"
                );

                if (champYield) {

                    const valeurYield = champYield.value.trim();

                    if (valeurYield === "") {

                        donnees["Yield"] = null;

                    } else {

                        const valeurNormalisee =
                            valeurYield.toLowerCase();

                        if (
                            ["null", "none", "nan", "na"].includes(
                                valeurNormalisee
                            )
                        ) {

                            donnees["Yield"] = null;

                        } else {

                            const valeurNumerique = Number(
                                valeurYield
                            );

                            if (
                                !Number.isFinite(valeurNumerique) ||
                                valeurNumerique < 0
                            ) {

                                afficherMessage(
                                    "message-individuel",
                                    "Yield doit être un nombre " +
                                    "positif ou nul.",
                                    "erreur"
                                );

                                return;
                            }

                            donnees["Yield"] = valeurNumerique;
                        }
                    }
                }

                // ----------------------------------
                // 6. Envoyer les données à FastAPI
                // ----------------------------------

                const bouton = document.getElementById(
                    "btn-predire-individuel"
                );

                if (!bouton) return;

                bouton.disabled = true;
                bouton.textContent = "Prédiction en cours...";

                try {

                    const reponse = await fetch(
                        "/api/predictions",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify(donnees)
                        }
                    );

                    const data = await lireReponse(reponse);

                    // ----------------------------------
                    // 7. Afficher les deux rendements
                    // ----------------------------------

                    afficherResultatIndividuel(data);

                    // ----------------------------------
                    // 8. Afficher la version du modèle
                    // ----------------------------------

                    if (data.version_modele) {

                        const version = document.getElementById(
                            "version-individuelle"
                        );

                        if (version) {

                            version.textContent =
                                data.version_modele;
                        }
                    }

                    // ----------------------------------
                    // 9. Message de succès
                    // ----------------------------------

                    afficherMessage(
                        "message-individuel",
                        "Prédiction effectuée avec succès.",
                        "succes"
                    );

                } catch (erreur) {

                    masquerResultatIndividuel();

                    afficherMessage(
                        "message-individuel",
                        erreur.message,
                        "erreur"
                    );

                } finally {

                    bouton.disabled = false;
                    bouton.textContent = "Prédire";
                }
            }
        );
    }


    // ======================================
    // 5. SELECTION DU FICHIER CSV
    // ======================================

    function afficherNomFichier(fichier) {

        if (!nomFichier) return;

        nomFichier.textContent = fichier
            ? `Fichier sélectionné : ${fichier.name}`
            : "";
    }


    if (fichierCSV) {

        fichierCSV.addEventListener(
            "change",
            () => {

                const fichier = fichierCSV.files[0];

                afficherNomFichier(fichier);
            }
        );
    }


    // ======================================
    // 6. GLISSER-DEPOSER DU CSV
    // ======================================

    if (zoneImport && fichierCSV) {

        zoneImport.addEventListener(
            "dragover",
            (event) => {

                event.preventDefault();

                zoneImport.classList.add(
                    "zone-import-active"
                );
            }
        );


        zoneImport.addEventListener(
            "dragleave",
            (event) => {

                event.preventDefault();

                zoneImport.classList.remove(
                    "zone-import-active"
                );
            }
        );


        zoneImport.addEventListener(
            "drop",
            (event) => {

                event.preventDefault();

                zoneImport.classList.remove(
                    "zone-import-active"
                );

                const fichiers = event.dataTransfer.files;

                if (!fichiers.length) return;

                const fichier = fichiers[0];

                if (
                    !fichier.name.toLowerCase().endsWith(".csv")
                ) {

                    afficherMessage(
                        "message-csv",
                        "Veuillez sélectionner un fichier au format CSV.",
                        "erreur"
                    );

                    return;
                }

                // Associer le fichier déposé au champ.
                const transfert = new DataTransfer();

                transfert.items.add(fichier);

                fichierCSV.files = transfert.files;

                afficherNomFichier(fichier);

                afficherMessage(
                    "message-csv",
                    "",
                    "info"
                );
            }
        );
    }


    // ======================================
    // 7. IMPORT ET PREDICTION CSV
    // ======================================

    if (formCSV) {

        formCSV.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                const fichier = fichierCSV?.files[0];

                if (!fichier) {

                    afficherMessage(
                        "message-csv",
                        "Veuillez sélectionner un fichier CSV.",
                        "erreur"
                    );

                    return;
                }

                if (
                    !fichier.name.toLowerCase().endsWith(".csv")
                ) {

                    afficherMessage(
                        "message-csv",
                        "Le fichier doit être au format CSV.",
                        "erreur"
                    );

                    return;
                }

                const bouton = document.getElementById(
                    "btn-predire-csv"
                );

                const lienTelechargement = document.getElementById(
                    "telecharger-resultat"
                );

                const conteneurTableau = document.getElementById(
                    "conteneur-tableau-csv"
                );

                const corpsTableau = document.getElementById(
                    "corps-tableau-csv"
                );

                if (!bouton) return;

                // ----------------------------------
                // 1. Réinitialiser les anciens résultats
                // ----------------------------------

                const lignesAcceptees = document.getElementById(
                    "lignes-acceptees"
                );

                const lignesRefusees = document.getElementById(
                    "lignes-refusees"
                );

                const lignesTotal = document.getElementById(
                    "lignes-total"
                );

                if (lignesAcceptees) {
                    lignesAcceptees.textContent = "—";
                }

                if (lignesRefusees) {
                    lignesRefusees.textContent = "—";
                }

                if (lignesTotal) {
                    lignesTotal.textContent = "—";
                }

                if (blocResultatsCSV) {
                    blocResultatsCSV.hidden = true;
                }

                if (lienTelechargement) {

                    lienTelechargement.hidden = true;

                    lienTelechargement.removeAttribute(
                        "href"
                    );
                }

                if (conteneurTableau) {
                    conteneurTableau.hidden = true;
                }

                if (corpsTableau) {
                    corpsTableau.replaceChildren();
                }

                // ----------------------------------
                // 2. Préparer le fichier
                // ----------------------------------

                const formulaire = new FormData();

                formulaire.append("file", fichier);

                bouton.disabled = true;
                bouton.textContent = "Traitement en cours...";

                afficherMessage(
                    "message-csv",
                    "",
                    "info"
                );

                try {

                    // ----------------------------------
                    // 3. Envoyer le CSV à FastAPI
                    // ----------------------------------

                    const reponse = await fetch(
                        "/api/predictions/csv",
                        {
                            method: "POST",
                            body: formulaire
                        }
                    );

                    const data = await lireReponse(reponse);

                    // ----------------------------------
                    // 4. Afficher les statistiques
                    // ----------------------------------

                    if (lignesAcceptees) {

                        lignesAcceptees.textContent =
                            data.nb_acceptees ??
                            data.lignes_acceptees ??
                            "—";
                    }

                    if (lignesRefusees) {

                        lignesRefusees.textContent =
                            data.nb_refusees ??
                            data.lignes_refusees ??
                            "—";
                    }

                    if (lignesTotal) {

                        lignesTotal.textContent =
                            data.total ??
                            data.lignes_total ??
                            "—";
                    }

                    if (blocResultatsCSV) {
                        blocResultatsCSV.hidden = false;
                    }

                    // ----------------------------------
                    // 5. Afficher la version du modèle
                    // ----------------------------------

                    if (data.version_modele) {

                        const version = document.getElementById(
                            "version-csv"
                        );

                        if (version) {

                            version.textContent =
                                data.version_modele;
                        }
                    }

                    // ----------------------------------
                    // 6. Afficher les résultats CSV
                    // ----------------------------------

                    if (
                        Array.isArray(data.resultats) &&
                        corpsTableau
                    ) {

                        data.resultats.forEach((ligne) => {

                            const tr = document.createElement(
                                "tr"
                            );

                            // 5 colonnes :
                            // Ligne
                            // Statut
                            // Rendement réel
                            // Rendement prédit
                            // Motif

                            const valeurs = [
                                ligne.ligne,
                                ligne.statut,
                                formaterRendement(
                                    ligne.rendement_reel
                                ),
                                formaterRendement(
                                    ligne.rendement_predit
                                ),
                                ligne.motif || "—"
                            ];

                            valeurs.forEach((valeur) => {

                                const td = document.createElement(
                                    "td"
                                );

                                td.textContent = String(valeur);

                                tr.appendChild(td);
                            });

                            corpsTableau.appendChild(tr);
                        });

                        if (conteneurTableau) {
                            conteneurTableau.hidden = false;
                        }
                    }

                    // ----------------------------------
                    // 7. Activer le téléchargement
                    // ----------------------------------

                    if (
                        lienTelechargement &&
                        data.lot_id !== undefined &&
                        data.lot_id !== null
                    ) {

                        lienTelechargement.href =
                            data.url_export ||
                            `/api/lots/${data.lot_id}/export`;

                        lienTelechargement.hidden = false;
                    }

                    // ----------------------------------
                    // 8. Message de succès
                    // ----------------------------------

                    afficherMessage(
                        "message-csv",
                        "Import et prédictions terminés avec succès.",
                        "succes"
                    );

                } catch (erreur) {

                    afficherMessage(
                        "message-csv",
                        erreur.message,
                        "erreur"
                    );

                } finally {

                    bouton.disabled = false;
                    bouton.textContent = "Prédire";
                }
            }
        );
    }

});
