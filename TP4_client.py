"""\
GLO-2000 Travail pratique 4 - Client
Noms et numéros étudiants:
-
-
-
"""

import argparse
import getpass
import json
import socket
import sys

import glosocket
import gloutils


class Client:
    """Client pour le serveur mail @glo2000.ca."""

    def __init__(self, destination: str) -> None:
        """
        Prépare et connecte le socket du client `_socket`.

        Prépare un attribut `_username` pour stocker le nom d'utilisateur
        courant. Laissé vide quand l'utilisateur n'est pas connecté.
        """
        # Préparation du socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(destination)

        #Préparation des membres
        self._destination = destination
        self._username = None

    def _register(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_REGISTER`.

        Si la création du compte s'est effectuée avec succès, l'attribut
        `_username` est mis à jour, sinon l'erreur est affichée.
        """
        userNom = input("Entrez un nom d'utilisateur:")
        motDePasse = getpass.getpass("Entrez un mot de passe:")
        regPayload = gloutils.AuthPayload(username=userNom,
                             password=motDePasse)
        messageAuth = gloutils.GloMessage(header=gloutils.Headers.AUTH_REGISTER,
                                          payload= gloutils.AuthPayload(username=userNom, password=motDePasse))
        glosocket.send_mesg(self._socket, json.dump(messageAuth))
        
        # Recevoir la réponse du serveur
        response = glosocket.recv_mesg(self._socket)
        match json.loads(response):
            case {"header": gloutils.Headers.OK}:
                self._username = userNom
            case {"header": gloutils.Headers.ERROR}:
                print(response['payload']['error_message'])

    def _login(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_LOGIN`.

        Si la connexion est effectuée avec succès, l'attribut `_username`
        est mis à jour, sinon l'erreur est affichée.
        """

        print("Connexion à un compte existant:")
        nomDUtilisateur = input("Nom d'utilisateur : ")
        motDePasse = getpass.getpass("Mot de passe : ")

        # Envoyer l'entête AUTH_LOGIN au serveur avec les informations de connexion
        self._socket.sendall(glosocket.encode_message(glosocket.AUTH_LOGIN))
        self._socket.sendall(glosocket.encode_message(nomDUtilisateur))
        self._socket.sendall(glosocket.encode_message(motDePasse))

        # Recevoir la réponse du serveur
        response = glosocket.receive_message(self._socket)

        if response == glosocket.OK:
            print("Connexion réussie.")
            self._username = nomDUtilisateur
        else:
            print("Erreur lors de la connexion. Veuillez réessayer.")

    def _quit(self) -> None:
        """
        Préviens le serveur de la déconnexion avec l'entête `BYE` et ferme le
        socket du client.
        """
        # Envoyer l'entête BYE au serveur
        self._socket.sendall(glosocket.encode_message(glosocket.BYE))

        # Fermer le socket du client
        self._socket.close()

    def _read_email(self) -> None:
        """
        Demande au serveur la liste de ses courriels avec l'entête
        `INBOX_READING_REQUEST`.

        Affiche la liste des courriels puis transmet le choix de l'utilisateur
        avec l'entête `INBOX_READING_CHOICE`.

        Affiche le courriel à l'aide du gabarit `EMAIL_DISPLAY`.

        S'il n'y a pas de courriel à lire, l'utilisateur est averti avant de
        retourner au menu principal.
        """

    def _send_email(self) -> None:
        """
        Demande à l'utilisateur respectivement:
        - l'adresse email du destinataire,
        - le sujet du message,
        - le corps du message.

        La saisie du corps se termine par un point seul sur une ligne.

        Transmet ces informations avec l'entête `EMAIL_SENDING`.
        """

    def _check_stats(self) -> None:
        """
        Demande les statistiques au serveur avec l'entête `STATS_REQUEST`.

        Affiche les statistiques à l'aide du gabarit `STATS_DISPLAY`.
        """

    def _logout(self) -> None:
        """
        Préviens le serveur avec l'entête `AUTH_LOGOUT`.

        Met à jour l'attribut `_username`.
        """
        glosocket.send_mesg(gloutils.GloMessage(header=gloutils.Headers.AUTH_LOGOUT))
        self._socket.close()
        self._username = None

    def run(self) -> None:
        """Point d'entrée du client."""
        should_quit = False

        while not should_quit:
            if not self._username:
                # Authentication menu
                print(gloutils.CLIENT_AUTH_CHOICE)
                choice = input("Entrez votre choix [1-3]:")
                match choice:
                    case "1":
                        self._register()
                    case "2":
                        self._login()
                    case "3":
                        self._quit()
                        should_quit = True
                    case other:

                else:
                    print("Choix invalide. Veuillez réessayer.")
            else:
                # Main menu
                print("Menu principal")
                print("1. Consultation de courriels")
                print("2. Envoi de courriels")
                print("3. Statistiques")
                print("4. Se déconnecter")
                choice = input("Entrez votre choix [1-4]: ")

                if choice == "1":
                    self._read_email()
                elif choice == "2":
                    self._send_email()
                elif choice == "3":
                    self._check_stats()
                elif choice == "4":
                    self._logout()
                else:
                    print("Choix invalide. Veuillez réessayer.")


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--destination", action="store",
                        dest="dest", required=True,
                        help="Adresse IP/URL du serveur.")
    args = parser.parse_args(sys.argv[1:])
    client = Client(args.dest)
    client.run()
    return 0


if __name__ == '__main__':
    sys.exit(_main())
