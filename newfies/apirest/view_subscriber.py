# -*- coding: utf-8 -*-
#
# Newfies-Dialer License
# http://www.newfies-dialer.org
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2013 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#

from rest_framework import viewsets
from rest_framework.response import Response
from apirest.subscriber_serializers import SubscriberSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from dialer_contact.models import Phonebook, Contact
from dialer_contact.constants import CONTACT_STATUS
from dialer_campaign.models import Campaign, Subscriber
from dialer_campaign.constants import SUBSCRIBER_STATUS
import logging
logger = logging.getLogger('newfies.filelog')


class SubscriberViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows campaigns to be viewed or edited.
    """
    queryset = Subscriber.objects.all()
    serializer_class = SubscriberSerializer
    authentication = (BasicAuthentication, SessionAuthentication)
    permissions = (IsAuthenticatedOrReadOnly, )

    def list(self, request):
        """
        This view should return a list of all the subscribers
        for the currently authenticated campaign user.
        """
        if self.request.user.is_superuser:
            queryset = Subscriber.objects.all()
        else:
            queryset = Subscriber.objects.filter(campaign__user=self.request.user)
        serializer = SubscriberSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Customize create"""
        phonebook_id = request.POST.get('phonebook_id')
        obj_phonebook = Phonebook.objects.get(id=phonebook_id)

        #this method will also create a record into Subscriber
        #this is defined in signal post_save_add_contact
        Contact.objects.create(
            contact=request.POST.get('contact'),
            last_name=request.POST.get('last_name'),
            first_name=request.POST.get('first_name'),
            email=request.POST.get('email'),
            description=request.POST.get('description'),
            status=CONTACT_STATUS.ACTIVE,  # default active
            phonebook=obj_phonebook)

        # Insert the contact to the subscriber also for
        # each campaign using this phonebook

        campaign_obj = Campaign.objects.filter(
            phonebook=obj_phonebook,
            user=request.user)

        for c_campaign in campaign_obj:
            imported_phonebook = []
            if c_campaign.imported_phonebook:
                # for example:- c_campaign.imported_phonebook = 1,2,3
                # So convert imported_phonebook string into int list
                imported_phonebook = map(int,
                    c_campaign.imported_phonebook.split(','))

            phonebook_list = c_campaign.phonebook\
                .values_list('id', flat=True)\
                .all()
            phonebook_list = map(int, phonebook_list)

            common_phonebook_list = []
            if phonebook_list:
                common_phonebook_list = list(set(imported_phonebook) & set(phonebook_list))
                if common_phonebook_list:
                    contact_list = Contact.objects\
                        .filter(
                            phonebook__in=common_phonebook_list,
                            status=CONTACT_STATUS.ACTIVE)
                    for con_obj in contact_list:
                        try:
                            Subscriber.objects.create(
                                contact=con_obj,
                                duplicate_contact=con_obj.contact,
                                status=SUBSCRIBER_STATUS.PENDING,  # PENDING
                                campaign=c_campaign)
                        except:
                            error_msg = "Duplicate Subscriber"
                            logger.error(error_msg)
                            pass

        logger.debug('Subscriber POST API : result ok 200')
        return Response({'status': 'Contact created'})