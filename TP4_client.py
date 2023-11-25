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
import re

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
        try:
            glosocket.send_mesg(self._socket, json.dumps(messageAuth))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._quit()

        # Recevoir la réponse du serveur
        try:
            reponse = json.loads(glosocket.recv_mesg(self._socket))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._quit()

        match reponse:
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
        authLogMessage = gloutils.GloMessage(
            header=gloutils.Headers.AUTH_LOGIN,
            payload=gloutils.AuthPayload(username=nomDUtilisateur,
                                         password=motDePasse)
        )
        try:
            glosocket.send_mesg(self._socket, json.dumps(authLogMessage))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._quit()

        # Recevoir la réponse du serveur
        try:
            reponse = json.loads(glosocket.recv_mesg(self._socket))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._quit()

        match reponse:
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
        try:
            glosocket.send_mesg(self._socket, json.dumps(gloutils.GloMessage(
                header=gloutils.Headers.BYE,
                payload=None
            )))
        except glosocket.GLOSocketError:
            print("Erreur lors de la deconnexion au serveur!")
            self._socket.close()
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
        # Demander la liste des courriels au serveur
        demandeEmailList = gloutils.GloMessage(
            header=gloutils.Headers.INBOX_READING_REQUEST
        )
        try:
            glosocket.send_mesg(self._socket, json.dumps(demandeEmailList))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()

        # Recevoir la réponse du serveur
        try:
            reponseEmailList = json.loads(glosocket.recv_mesg(self._socket))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()

        emailList: list = reponseEmailList['payload']['email_list']
        if len(emailList) < 1:
            return
        else:
            for courriel in emailList:
                print(courriel)
            # Demander le choix de l'utilisateur
            choixCourriel = input("Entrez votre choix [1-" + str(len(emailList)) + "]:")
            if not (re.search(r"[0-9]+", choixCourriel) is not None) and (not choixCourriel>len(emailList)):
                print("Erreur, choix invalide!")
                return
            else:
                #Envoi du numéro du courriel choisi
                envoiChoix = gloutils.GloMessage(
                    header=gloutils.Headers.INBOX_READING_CHOICE,
                    payload=gloutils.EmailChoicePayload(choice=choixCourriel)
                )
                try:
                    glosocket.send_mesg(self._socket, json.dumps(envoiChoix))
                except glosocket.GLOSocketError:
                    print("Erreur, la connexion avec le serveur est rompue!")
                    self._username = None
                    self._quit()

                #Reception du courriel choisi
                try:
                    receptionEmail = json.loads(glosocket.recv_mesg(self._socket))
                except glosocket.GLOSocketError:
                    print("Erreur, la connexion avec le serveur est rompue!")
                    self._username = None
                    self._quit()
                except json.JSONDecodeError:
                    print("Erreur, de communication avec le serveur!\nVeuillez vous reconnecter")
                    self._username = None
                    self._logout()
                
                print(gloutils.EMAIL_DISPLAY.format(
                    sender=receptionEmail["payload"]['sender'],
                    to=receptionEmail["payload"]['destination'],
                    subject=receptionEmail["payload"]['subject'],
                    date=receptionEmail["payload"]['date'],
                    body=receptionEmail["payload"]['content']))

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
        emailContenu = gloutils.EmailContentPayload(
            sender=self._username + '@' + gloutils.SERVER_DOMAIN,
            destination=destEmail,
            subject=sujEmail,
            date=gloutils.get_current_utc_time(),
            content=messageEmail)
        #Envoi de courriel
        emailSent = gloutils.GloMessage(
            header=gloutils.Headers.EMAIL_SENDING,
            payload=emailContenu)
        
        try:
            glosocket.send_mesg(self._socket, json.dumps(emailSent))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()

        # Confirmation de l'envoi.
        try:
            reponseServeur = json.loads(glosocket.recv_mesg(self._socket))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()
        
        match reponseServeur:
            case {"header": gloutils.Headers.OK}:
                print("Courriel envoyé avec succès")
            case {"header": gloutils.Headers.ERROR}:
                print(reponseServeur['payload']['error_message'])
            case _:
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
        try:
            glosocket.send_mesg(self._socket, json.dumps(demandeStats))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()
        
        #Réception des statistiques et affichage.
        try:
            stats =json.loads(glosocket.recv_mesg(self._socket))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()
        match stats:
            case {"header": gloutils.Headers.OK}:
                if 'payload' in stats:
                    affichageStats = gloutils.STATS_DISPLAY.format(
                        count=stats["payload"]["count"],
                        size=stats["payload"]["size"])
                    print(affichageStats)
                else:
                    print("Erreur lors l'accès aux statistiques.")
            case _:
                print("Erreur lors l'accès aux statistiques.")

    def _logout(self) -> None:
        """
        Préviens le serveur avec l'entête `AUTH_LOGOUT`.

        Met à jour l'attribut `_username`.
        """
        logOutMessage = gloutils.GloMessage(
            header=gloutils.Headers.AUTH_LOGOUT)
        try:
            glosocket.send_mesg(self._socket, json.dumps(logOutMessage))
        except glosocket.GLOSocketError:
            print("Erreur, la connexion avec le serveur est rompue!")
            self._username = None
            self._quit()

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
                        try:
                            self._register()
                        except glosocket.GLOSocketError:
                            print("Erreur, la connexion avec le serveur est rompue!")
                            self._quit()
                            should_quit = True
                            continue
                        continue
                    case "2":
                        try:
                            self._login()
                        except glosocket.GLOSocketError:
                            print("Erreur, la connexion avec le serveur est rompue!")
                            self._quit()
                            should_quit = True
                            continue
                        continue
                    case "3":
                        self._quit()
                        should_quit = True
                        continue
                    case _: 
                        pass
            else:
                # Main menu
                print(gloutils.CLIENT_USE_CHOICE)
                choixMenuEmail = input("Entrez votre choix [1-4]: ")
                match choixMenuEmail:
                    case "1":
                        try:
                            self._read_email()
                        except glosocket.GLOSocketError:
                            print("Erreur, la connexion avec le serveur est rompue!")
                            self._username = None
                            self._quit()
                            should_quit = True
                            continue
                    case "2":
                        try:
                            self._send_email()
                        except glosocket.GLOSocketError:
                            print("Erreur, la connexion avec le serveur est rompue!")
                            self._username = None
                            self._quit()
                            should_quit = True
                            continue
                    case "3":
                        try:
                            self._check_stats()
                        except glosocket.GLOSocketError:
                            print("Erreur, la connexion avec le serveur est rompue!")
                            self._username = None
                            self._quit()
                            should_quit = True
                            continue
                    case "4":
                        try:
                            self._logout()
                        except glosocket.GLOSocketError:
                            print("Erreur, la connexion avec le serveur est rompue!")
                            self._username = None
                            self._quit()
                            should_quit = True
                            continue
                        continue
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
