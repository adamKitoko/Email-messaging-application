"""\
GLO-2000 Travail pratique 4 - Serveur
Noms et numéros étudiants:
- Dominique Saint-Pierre 111 134 516
- Adam Kitoko 536 868 700
- Pengdwindé Alex Auguste Ouedraogo 111 250 058
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
        except OSError:
            print("Erreur lors de la création du socket_serveur")
            sys.exit(-1)
        try:
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except OSError:
            print("Erreur lors de la création du socket_serveur")
            sys.exit(-1)
        try:
            self._server_socket.bind(("127.0.0.1", gloutils.APP_PORT))
        except OSError:
            print("Erreur lors de la création du socket_serveur")
            sys.exit(-1)
        try:
            self._server_socket.listen()
        except OSError:
            print("Erreur lors de la création du socket_serveur")
            sys.exit(-1)
        # self._client_socs
        self._client_socs: list[socket.socket] = []

        # self._logged_users
        self._logged_users: dict = {}
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
        client_socket, socket_addr = self._server_socket.accept()
        self._client_socs.append(client_socket)

    def _remove_client(self, client_soc: socket.socket) -> None:
        """Retire le client des structures de données et ferme sa connexion."""
        if client_soc in self._logged_users:
            self._logged_users.pop(client_soc)
        if client_soc in self._client_socs:
            self._client_socs.remove(client_soc)
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
            userDossier = (pathlib.Path(gloutils.SERVER_DATA_DIR))/payload['username']
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
            reponse = gloutils.GloMessage(header=gloutils.Headers.ERROR,
                                      payload=gloutils.ErrorPayload(error_message=errMessage))
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
            if hmac.compare_digest(hasherPass.hexdigest(),(chemin/payload['username']/gloutils.PASSWORD_FILENAME).read_text()):
                self._logged_users[client_soc] = payload['username']
                reponse = gloutils.GloMessage(header=gloutils.Headers.OK)
            else:
                # Mot de passe invalide, envoi d'un message d'erreur.
                reponse = gloutils.GloMessage(header=gloutils.Headers.ERROR,
                                               payload=gloutils.ErrorPayload(error_message="Le mot de passe est invalide"))
        else:
            # Le nom d'utilisateur est invalide, envoi d'un message d'erreur.
            reponse = gloutils.GloMessage(header=gloutils.Headers.ERROR,
                                           payload=gloutils.ErrorPayload(error_message="Le nom d'utilisateur est invalide"))
        return reponse

    def _logout(self, client_soc: socket.socket) -> None:
        """Déconnecte un utilisateur."""
        self._logged_users.pop(client_soc)

    def _get_email_list(self, client_soc: socket.socket
                        ) -> gloutils.GloMessage:
        """
        Récupère la liste des courriels de l'utilisateur associé au socket.
        Les éléments de la liste sont construits à l'aide du gabarit
        SUBJECT_DISPLAY et sont ordonnés du plus récent au plus ancien.

        Une absence de courriel n'est pas une erreur, mais une liste vide.
        """
        cheminUser = pathlib.Path(gloutils.SERVER_DATA_DIR, self._logged_users[client_soc])
        emailList: list = []
        emailCompte = 0
        for email in sorted(cheminUser.iterdir(), key=os.path.getmtime, reverse=True):
            if not email.samefile(cheminUser/gloutils.PASSWORD_FILENAME):
                emailCompte += 1
                emailJson = (json.loads(email.read_text()))
                emailList.append(gloutils.SUBJECT_DISPLAY.format(
                    number=emailCompte,
                    sender=emailJson['sender'],
                    subject=emailJson['subject'],
                    date=emailJson['date']))
        repEmailList = gloutils.GloMessage(
            header=gloutils.Headers.OK,
            payload=gloutils.EmailListPayload(email_list=emailList)
        )

        return repEmailList

    def _get_email(self, client_soc: socket.socket,
                   payload: gloutils.EmailChoicePayload
                   ) -> gloutils.GloMessage:
        """
        Récupère le contenu de l'email dans le dossier de l'utilisateur associé
        au socket.
        """
        cheminUser = pathlib.Path(gloutils.SERVER_DATA_DIR, self._logged_users[client_soc])
        emailList: list = []
        for email in sorted(cheminUser.iterdir(), key=os.path.getmtime, reverse=True):
            if not email.samefile(cheminUser/gloutils.PASSWORD_FILENAME):
                emailList.append(email)
        emailReq = json.loads(emailList[int(payload["choice"]) - 1].read_text())
        return gloutils.GloMessage(
            header=gloutils.Headers.OK,
            payload=emailReq
        )

    def _get_stats(self, client_soc: socket.socket) -> gloutils.GloMessage:
        """
        Récupère le nombre de courriels et la taille du dossier et des fichiers
        de l'utilisateur associé au socket.
        """
        cheminUser = (pathlib.Path(gloutils.SERVER_DATA_DIR))/self._logged_users[client_soc]

        #Nombre de courriel.
        countStats = 0
        sizeStats = 0
        for fichier in cheminUser.iterdir():
            if fichier == cheminUser/gloutils.PASSWORD_FILENAME:
                pass
            else:
                countStats += 1
                sizeStats += fichier.stat().st_size

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
        if re.search(r"(@[a-zA-Z0-9]+\.[a-zA-Z]+)$", payload['destination']) is not None:
            if re.search(r"(@"+gloutils.SERVER_DOMAIN+")$", payload['destination']) is not None:
                if ((pathlib.Path(gloutils.SERVER_DATA_DIR))/(re.split(r"(@[a-zA-Z0-9]+\.[a-zA-Z]+)$", payload["destination"])[0])).exists():
                    #Destination interne
                    cheminUtilisateur = (pathlib.Path(gloutils.SERVER_DATA_DIR))/(re.split(r"(@[a-zA-Z0-9]+\.[a-zA-Z]+)$", payload["destination"])[0])
                    try:
                        (cheminUtilisateur/(payload["date"]+payload["sender"])).write_text(json.dumps(payload))
                    except FileExistsError:
                        print("erreur, le fichier existe déjà!")
                    emailConfirmation = gloutils.GloMessage(
                        header=gloutils.Headers.OK
                    )
                else:
                    # Destinataire interne inconnu
                    cheminPerdu = (pathlib.Path(gloutils.SERVER_DATA_DIR))/gloutils.SERVER_LOST_DIR
                    try:
                        (cheminPerdu/(payload["date"]+payload["destination"])).write_text(json.dumps(payload))
                    except FileExistsError:
                        print("Erreur, le fichier existe déjà!")
                    emailConfirmation = gloutils.GloMessage(
                        header=gloutils.Headers.ERROR,
                        payload=gloutils.ErrorPayload(error_message="""Une erreur est survenue lors de l'envoi du message!\nL'addresse de destination est invalide"""))
        else:
            #Destination externe
            emailConfirmation = gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(error_message="""Une erreur est survenue lors de l'envoi du message!
                                                L'addresse de destination est invalide"""))

        return emailConfirmation

    def run(self):
        """Point d'entrée du serveur."""
        waiters = []
        while True:
            # Select readable sockets
            # try:
            #     result = select.select([self._server_socket] + self._client_socs, [], [])
            # except TypeError:
            #     print("Erreur lors de la selection.")
            #     sys.exit(-1)
            result = select.select([self._server_socket] + self._client_socs, [], [])
            waiters: list[socket.socket] = result[0]
            for waiter in waiters:
                # Handle sockets
                if waiter == self._server_socket:
                    self._accept_client()
                else:
                    try:
                        message = json.loads(glosocket.recv_mesg(waiter))
                    except json.JSONDecodeError:
                        self._remove_client(waiter)
                        print("Erreur lors de l'authentification du socket")
                        # print("Erreur lors de l'extraction des infos du messages.")
                        continue
                    except glosocket.GLOSocketError:
                        self._remove_client(waiter)
                        print("Erreur lors de l'authentification du socket")
                        continue
                    # if headers et payload present.
                    #
                    if message['header'] is not None:
                        match message:
                            case {"header": gloutils.Headers.BYE}:
                                self._remove_client(waiter)
                            #AUTH_REGISTER
                            case {"header": gloutils.Headers.AUTH_REGISTER}:
                                if ("username" in message['payload'] and "password" in message['payload']):
                                    regReponse = self._create_account(waiter, message['payload'])
                                    glosocket.send_mesg(waiter, json.dumps(regReponse))
                                    continue
                                else:
                                    print("Erreur le message ne contient pas et/ou pas le bon gloutils.payload")
                                    self._remove_client(waiter)
                                    continue
                            #AUTH_LOGIN
                            case {"header": gloutils.Headers.AUTH_LOGIN}:
                                authLogReponse = self._login(waiter, message['payload'])
                                try:
                                    glosocket.send_mesg(waiter, json.dumps(authLogReponse))
                                except glosocket.GLOSocketError:
                                    print("Erreur lors de l'envoi de la confirmation de connextion par le serveur.")
                                continue
                            #AUTH_LOGOUT
                            case {"header": gloutils.Headers.AUTH_LOGOUT}:
                                self._logout(waiter)
                                continue
                            #STATS_REQUEST
                            case {"header": gloutils.Headers.STATS_REQUEST}:
                                try:
                                    demandeStats = self._get_stats(waiter)
                                except OSError:
                                    print("Erreur la demande de statistique.")
                                    pass
                                try:
                                    glosocket.send_mesg(waiter, json.dumps(demandeStats))
                                except glosocket.GLOSocketError:
                                    print("Erreur lors de l'envoi d'une demande de statistiques.")
                                    self._remove_client(waiter)
                                    continue
                            #EMAIL_SENDING
                            case {"header": gloutils.Headers.EMAIL_SENDING}:
                                glosocket.send_mesg(waiter, json.dumps(self._send_email(message["payload"])))
                            case {"header": gloutils.Headers.INBOX_READING_REQUEST}:
                                glosocket.send_mesg(waiter, json.dumps(self._get_email_list(waiter)))
                            case {"header": gloutils.Headers.INBOX_READING_CHOICE}:
                                glosocket.send_mesg(waiter, json.dumps(self._get_email(waiter, message['payload'])))

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
