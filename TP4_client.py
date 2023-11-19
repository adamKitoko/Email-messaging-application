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
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((destination, gloutils.APP_PORT))
        except glosocket.GLOSocketError:
            sys.exit(-1)
        
        #Préparation des membres
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
        messageAuth = gloutils.GloMessage(header=gloutils.Headers.AUTH_REGISTER,
                                          payload= gloutils.AuthPayload(username=userNom, password=motDePasse))
        glosocket.send_mesg(self._socket, json.dumps(messageAuth))

        # Recevoir la réponse du serveur
        reponse = glosocket.recv_mesg(self._socket)
        match json.loads(reponse):
            case {"header": gloutils.Headers.OK}:
                self._username = userNom
            case {"header": gloutils.Headers.ERROR}:
                errPayload = reponse['payload']
                print(errPayload['error_message'])

    def _login(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_LOGIN`.

        Si la connexion est effectuée avec succès, l'attribut `_username`
        est mis à jour, sinon l'erreur est affichée.
        """

        print("Connexion à un compte existant:")
        nomDUtilisateur = input("Entrez un nom d'utilisateur:")
        motDePasse = getpass.getpass("Entrez un mot de passe:")

        # Envoyer l'entête AUTH_LOGIN au serveur avec les informations de connexion
        self._socket.sendall(glosocket.encode_message(glosocket.AUTH_LOGIN))
        self._socket.sendall(glosocket.encode_message(nomDUtilisateur))
        self._socket.sendall(glosocket.encode_message(motDePasse))


        # Recevoir la réponse du serveur
        reponse = glosocket.recv_mesg(self._socket)
        match json.loads(reponse):
            case {"header": gloutils.Headers.OK}:
                self._username = nomDUtilisateur
            case {"header": gloutils.Headers.ERROR}:
                print(reponse['payload']['error_message'])

    def _quit(self) -> None:
        """
        Préviens le serveur de la déconnexion avec l'entête `BYE` et ferme le
        socket du client.
        """
        # Envoyer l'entête BYE au serveur
        glosocket.send_mesg(self._socket, json.dumps(gloutils.GloMessage(
            header=gloutils.Headers.BYE,
            payload=None
        )))

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
        #Récupération du contenu du courriel.
        destEmail = input("Entrez l'adresse du destinataire:")
        sujEmail = input("Entrez le sujet:")
        # Boucle d'entrée du contenu du email.
        print("Entrez le contenu du courriel, terminez la saisie avec un /'./' seul sur une ligne:")
        messageEmail = ""
        saisieTerm = False
        while (not saisieTerm):
            textSaisi = input()
            if (textSaisi == '.'):
                saisieTerm = True
            else:
                messageEmail += textSaisi

        # Préparation du courriel.
        emailContenu = gloutils.EMAIL_DISPLAY.format(
            source=self._username + '@' + gloutils.SERVER_DOMAIN,
            destination=destEmail,
            subject=sujEmail,
            date=gloutils.get_current_utc_time,
            content=messageEmail
        )
        #Envoi de courriel
        emailSent = gloutils.GloMessage(
            header=gloutils.Headers.EMAIL_SENDING,
            payload=emailContenu
        )
        glosocket.send_mesg(self._socket, json.dumps(emailContenu))

        # Confirmation de l'envoi.
        reponseServeur = json.loads(glosocket.recv_mesg(self._socket))
        match reponseServeur:
            case {"header": gloutils.Headers.OK}:
                print("Courriel envoyé avec succès")
            case {"header": gloutils.Headers.ERROR}:
                print(reponseServeur['payload']['error_message'])
            case other:
                print("Erreur lors de la confirmation de l'envoi.")

    def _check_stats(self) -> None:
        """
        Demande les statistiques au serveur avec l'entête `STATS_REQUEST`.

        Affiche les statistiques à l'aide du gabarit `STATS_DISPLAY`.
        """
        #Envoi de la demande de statistique.
        demandeStats = gloutils.GloMessage(
            header=gloutils.Headers.STATS_REQUEST
        )
        glosocket.send_mesg(self._socket, json.dumps(demandeStats))
        
        #Réception des statistiques et affichage.
        stats = glosocket.recv_mesg(self._socket)
        match json.loads(stats):
            case {"header": gloutils.Headers.OK}:
                if 'payload' in stats:
                    affichageStats = gloutils.STATS_DISPLAY.format(
                        count=stats["payload"]["count"],
                        size=stats["payload"]["size"])
                    print(affichageStats)
                else:
                    print("Erreur lors l'accès aux statistiques.")
            case other:
                print("Erreur lors l'accès aux statistiques.")

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
                choix = input("Entrez votre choix [1-3]:")
                match choix:
                    case "1":
                        self._register()
                        continue
                    case "2":
                        self._login()
                        continue
                    case "3":
                        should_quit = True
                        self._quit()
                    case _: 
                        pass
            else:
                # Main menu
                print(gloutils.CLIENT_USE_CHOICE)
                choixMenuEmail = input("Entrez votre choix [1-4]: ")
                match choixMenuEmail:
                    case "1":
                        self._read_email()
                    case "2":
                        self._send_email()
                    case "3":
                        self._check_stats()
                    case "4":
                        should_quit = True
                        self._quit
                    case _:
                        print("Choix invalide. Veuillez réessayer.")
                        pass


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
