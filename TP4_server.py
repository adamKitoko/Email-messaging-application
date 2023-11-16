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
            self._serveur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._serveur_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._serveur_socket.bind(("127.0.0.1", gloutils.APP_PORT))
            self._serveur_socket.listen()
        except OSError:
            print("Erreur lors de la création du socket_serveur")
            sys.exit(-1)
        # self._client_socs
        self._client_socs: list

        # self._logged_users
        self._logged_users: dict
        # ...
        server_data = pathlib.Path(gloutils.SERVER_DATA_DIR)
        lost_data = pathlib.Path(gloutils.SERVER_DATA_DIR + "/"
                                 + gloutils.SERVER_LOST_DIR)
        try:
            server_data.mkdir()
            lost_data.mkdir()
        except FileExistsError:
            pass

        # if not server_data.exist():

        # if "SERVEUR_DATA_DIR" not in os.listdir():
        #     os.mkdir("SERVEUR_DATA_DIR")
        # if "SERVER_LOST_DIR" not in os.listdir("./SERVER_DATA_DIR"):
        #     os.mkdir("./SERVER_LOST_DIR")

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
        return gloutils.GloMessage()

    def _login(self, client_soc: socket.socket, payload: gloutils.AuthPayload
               ) -> gloutils.GloMessage:
        """
        Vérifie que les données fournies correspondent à un compte existant.

        Si les identifiants sont valides, associe le socket à l'utilisateur et
        retourne un succès, sinon retourne un message d'erreur.
        """
        return gloutils.GloMessage()

    def _logout(self, client_soc: socket.socket) -> None:
        """Déconnecte un utilisateur."""
        self._remove_client(client_soc)
        """..."""

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
        return gloutils.GloMessage()

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
            result = select.select([self._serveur_socket]+self._client_socs, [], [])
            waiters: list[socket.socket] = result[0]
            for waiter in waiters:
                # Handle sockets
                if waiter == self._serveur_socket:
                    self._accept_client()
                else:
                    try:
                        message = json.loads(glosocket.recv_mesg(waiter))
                    except glosocket.GLOSocketError:
                        self._remove_client(waiter)
                        continue
                    # if headers et payload present.
                    #
                    match message['header']:
                        case gloutils.Headers.AUTH_REGISTER:
                            self._create_account(waiter, message['payload'])
                        case gloutils.Headers.AUTH_LOGIN:
                            self._login(waiter, message['payload'])
                        case gloutils.Headers.AUTH_LOGOUT:
                            self._logout(waiter)
                        
                match json.loads(message):
                    case {"header": gloutils.Headers.BYE}:
                        self._remove_client(waiter)

                pass


def _main() -> int:
    server = Server()
    try:
        server.run()
    except KeyboardInterrupt:
        server.cleanup()
    return 0


if __name__ == '__main__':
    sys.exit(_main())
