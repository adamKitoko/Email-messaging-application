"""\
GLO-2000 Travail pratique 4 - Serveur
Noms et numéros étudiants:
-
-
-
"""

import hashlib
import hmac
import json
import os
import pathlib
import select
import socket
import sys
import re

import glosocket
import gloutils


class Server:
    """Serveur mail @glo2000.ca."""

    def __init__(self) -> None:
        """
        Prépare le socket du serveur `_server_socket`
        et le met en mode écoute.

        Prépare les attributs suivants:
        - `_client_socs` une liste des sockets clients.
        - `_logged_users` un dictionnaire associant chaque
            socket client à un nom d'utilisateur.

        S'assure que les dossiers de données du serveur existent.
        """
        # self._server_socket
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("127.0.0.1", gloutils.APP_PORT))
            self._server_socket.listen()
        except OSError:
            print("Erreur lors de la création du socket_serveur")
            sys.exit(-1)
        # self._client_socs
        self._client_socs: list = []

        # self._logged_users
        self._logged_users: dict
        # ...
        try:
            pathlib.Path(gloutils.SERVER_DATA_DIR).mkdir()
        except FileExistsError:
            pass
        try:
            (pathlib.Path(gloutils.SERVER_DATA_DIR)/gloutils.SERVER_LOST_DIR).mkdir()
        except FileExistsError:
            pass

    def cleanup(self) -> None:
        """Ferme toutes les connexions résiduelles."""
        for client_soc in self._client_socs:
            client_soc.close()
        self._server_socket.close()

    def _accept_client(self) -> None:
        """Accepte un nouveau client."""
        client_socket, _ = self._serveur_socket.accept()
        self._client_socs.append(client_socket)

    def _remove_client(self, client_soc: socket.socket) -> None:
        """Retire le client des structures de données et ferme sa connexion."""
        if client_soc in self._client_socs:
            self._client_socs.remove(client_soc)
        if client_soc in self._logged_users:
            self._logged_users.pop(client_soc)
        client_soc.close()

    def _create_account(self, client_soc: socket.socket,
                        payload: gloutils.AuthPayload
                        ) -> gloutils.GloMessage:
        """
        Crée un compte à partir des données du payload.

        Si les identifiants sont valides, créee le dossier de l'utilisateur,
        associe le socket au nouvel l'utilisateur et retourne un succès,
        sinon retourne un message d'erreur.
        """
        #Message d'erreur.
        errMessage = """La création à échouée:
        - Le nom d'utilisateur est invalide.
        - Le mot de passe n'est pas assez sûr."""

        #Validation des informations fournis pas le client.
        if ((re.search(r"[a-zA-Z0-9_.-]+", payload['username']) is not None) 
            and (re.search(r"^(?=.*[A-Z])(?=.*\d).{10,}$", payload['password']) is not None)):

            # Création du dossier d'utilisateur
            userDossier = pathlib.Path(gloutils.SERVER_DATA_DIR)/payload['username']
            try:
                userDossier.mkdir()
            except FileExistsError:
                # Nom d'utilisateur déjà utilisé, Envoyer un messege ERROR
                errPayload = gloutils.ErrorPayload(error_message=errMessage)
                return gloutils.GloMessage(header=gloutils.Headers.ERROR,payload=errPayload)
            
            # Hachage du mot de passe.
            hasherPass = hashlib.sha3_512()
            hasherPass.update(payload['password'].encode('utf-8'))
            try:
                (pathlib.Path(gloutils.SERVER_DATA_DIR)/payload['username']/gloutils.PASSWORD_FILENAME).write_text(hasherPass.hexdigest())
            except FileExistsError:
                #Suppression du dossier utilisateur crée
                (pathlib.Path(gloutils.SERVER_DATA_DIR)/payload['username']).rmdir()
                return gloutils.GloMessage(header=gloutils.Headers.ERROR,
                                           payload=gloutils.ErrorPayload(error_message="Erreur lors de la création du compte d'utilisateur"))
            # Envoyer un message OK et association du socket
            self._logged_users[client_soc] = payload['username']
            reponse = gloutils.GloMessage(header=gloutils.Headers.OK)
            
        else:
            # Envoyer un message ERROR
            reponsePayLoad = gloutils.ErrorPayload(error_message=errMessage)
            reponse = gloutils.GloMessage(header=gloutils.Headers.ERROR,
                                      payload=reponsePayLoad)
        return reponse

    def _login(self, client_soc: socket.socket, payload: gloutils.AuthPayload
               ) -> gloutils.GloMessage:
        """
        Vérifie que les données fournies correspondent à un compte existant.

        Si les identifiants sont valides, associe le socket à l'utilisateur et
        retourne un succès, sinon retourne un message d'erreur.
        """
        chemin = pathlib.Path(gloutils.SERVER_DATA_DIR)
        if (chemin/payload['username']).exists():
            # Vérifier le mdp
            hasherPass = hashlib.sha3_512()
            hasherPass.update(payload['password'].encode('utf-8'))
            if (hasherPass == (chemin/gloutils.PASSWORD_FILENAME).read_text()):
                self._logged_users[client_soc] = payload['username']
                reponse = gloutils.GloMessage(header=gloutils.Headers.OK)
            else:
                # Mot de passe invalide, envoi d'un message d'erreur.
                errMessage = "Le mot de pass est invalide"
                errPayload = gloutils.ErrorPayload(error_message=errMessage)
                reponse = gloutils.GloMessage(header=gloutils.Headers.ERROR, payload=errPayload)
                return reponse
        else:
            # Mot de passe invalide, envoi d'un message d'erreur.
            errMessage = "Le nom d'utilisateur est invalide"
            errPayload = gloutils.ErrorPayload(error_message=errMessage)
            reponse = gloutils.GloMessage(header=gloutils.Headers.ERROR, payload=errPayload)
        return reponse

    def _logout(self, client_soc: socket.socket) -> None:
        """Déconnecte un utilisateur."""
        self._remove_client(client_soc)
        """..."""
        logOutMessage = gloutils.GloMessage(header=gloutils.Headers.AUTH_LOGOUT)
        glosocket.send_mesg(client_soc, json.dump(logOutMessage))

    def _get_email_list(self, client_soc: socket.socket
                        ) -> gloutils.GloMessage:
        """
        Récupère la liste des courriels de l'utilisateur associé au socket.
        Les éléments de la liste sont construits à l'aide du gabarit
        SUBJECT_DISPLAY et sont ordonnés du plus récent au plus ancien.

        Une absence de courriel n'est pas une erreur, mais une liste vide.
        """
        return gloutils.GloMessage()

    def _get_email(self, client_soc: socket.socket,
                   payload: gloutils.EmailChoicePayload
                   ) -> gloutils.GloMessage:
        """
        Récupère le contenu de l'email dans le dossier de l'utilisateur associé
        au socket.
        """
        return gloutils.GloMessage()

    def _get_stats(self, client_soc: socket.socket) -> gloutils.GloMessage:
        """
        Récupère le nombre de courriels et la taille du dossier et des fichiers
        de l'utilisateur associé au socket.
        """
        cheminUser = pathlib.Path(gloutils.SERVER_DATA_DIR)/self._logged_users[client_soc]

        #Nombre de courriel.
        countStats = 0
        for fichier in cheminUser.iterdir():
            if fichier == cheminUser/gloutils.PASSWORD_FILENAME:
                pass
            else:
                countStats += 1

        #Taille du dossier
        sizeStats = cheminUser.stat().st_size

        #Création du message d'envoi des statistiques au client.
        reponseStats = gloutils.GloMessage(
            header=gloutils.Headers.OK,
            payload=gloutils.StatsPayload(
                count=countStats,
                size=sizeStats
            )
        )
        return reponseStats

    def _send_email(self, payload: gloutils.EmailContentPayload
                    ) -> gloutils.GloMessage:
        """
        Détermine si l'envoi est interne ou externe et:
        - Si l'envoi est interne, écris le message tel quel dans le dossier
        du destinataire.
        - Si le destinataire n'existe pas, place le message dans le dossier
        SERVER_LOST_DIR et considère l'envoi comme un échec.
        - Si le destinataire est externe, considère l'envoi comme un échec.

        Retourne un messange indiquant le succès ou l'échec de l'opération.
        """
        return gloutils.GloMessage()

    def run(self):
        """Point d'entrée du serveur."""
        waiters = []
        while True:
            # Select readable sockets
            result = select.select([self._server_socket]+ self._client_socs, [], [])
            waiters: list[socket.socket] = result[0]
            for waiter in waiters:
                # Handle sockets
                if waiter == self._server_socket:
                    self._accept_client()
                else:
                    try:
                        message = json.loads(glosocket.recv_mesg(waiter))
                    except json.JSONDecodeError as e:
                        self._remove_client(waiter)
                        print("Erreur lors de la connection du socket: " + waiter.getpeername())
                        continue
                    # if headers et payload present.
                    #
                    if message['header'] is not None:
                        match message:
                            case {"header": gloutils.Headers.BYE}:
                                self._remove_client(waiter)
                            case {"header": gloutils.Headers.AUTH_REGISTER}:
                                if (message['payload'] == gloutils.AuthPayload):
                                    self._create_account(waiter, message['payload'])
                                else:
                                    print("Erreur le message ne contient pas et/ou pas le bon gloutils.payload")
                                    self._remove_client(waiter)
                                continue
                            case {"header": gloutils.Headers.AUTH_LOGIN}:
                                self._login(waiter, message['payload'])
                            case {"header": gloutils.Headers.AUTH_LOGOUT}:
                                self._logout(waiter)
                            case {"header": gloutils.Headers.STATS_REQUEST}:
                                try:
                                    glosocket.send_mesg(waiter, self._get_stats(waiter))
                                except glosocket.GLOSocketError:
                                    print("Erreur lors de l'envoi d'un message.")
                                    self._remove_client(waiter)
                                    continue
                    else:
                        print("Error le message ne contient pas de gloutils.Headers")
                        self._remove_client(waiter)
                        continue


def _main() -> int:
    server = Server()
    try:
        server.run()
    except KeyboardInterrupt:
        server.cleanup()
    return 0


if __name__ == '__main__':
    sys.exit(_main())
