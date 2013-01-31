from leaderboard.models import Team, Entry, MembershipRequest, user_is_member_of_team
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm
from django.conf import settings


def index(request):
	teams = Team.objects.all().order_by('name')
	data = dict(teams=teams)
	return render(request, 'leaderboard/team_list.html', data)


def detail(request, team_id):
	team = Team.objects.get(id=team_id)
	data = dict(team=team)
	return render(request, 'leaderboard/team_detail.html', data)

@login_required
def setup(request):
	profile = request.user.get_profile()
	teams = profile.teams.all()
	recent_entries = Entry.objects.filter(team__in=teams).order_by('-date')[:5]
	data=dict(teams=teams, entries=recent_entries)
	return render(request, 'leaderboard/team_setup.html', data)


class TeamCreationForm(ModelForm):
	class Meta:
		model = Team
		fields = ("name","notes")

@login_required
def create(request):
	if request.method=="POST":
		form = TeamCreationForm(request.POST)
		if form.is_valid():
			team = form.save()
			profile = request.user.get_profile()
			profile.teams.add(team)
			profile.save()
			return HttpResponseRedirect("/")
		else:
			data = dict(form=form)
			return render(request, "leaderboard/team_create.html", data)

	else:
		form = TeamCreationForm()
		data = dict(form=form)
		return render(request, "leaderboard/team_create.html", data)

@login_required
def join(request):
	teams = Team.objects.all()
	data = dict(teams=teams)
	return render(request, 'leaderboard/team_join.html', data)


def send_request_email(user, team, token):
	team_leader = team.users.order_by('user__date_joined')[0]
	subject = 'Great3 %s Membership request by %s' % (team, user)
	main_site = Site.objects.get_current()
	accept_link = "%s/leaderboard/team/accept/%s" % (main_site, token)
	reject_link = "%s/leaderboard/team/reject/%s" % (main_site, token)
	
	message = """
Dear %s,

A user called %s (email %s) has requested membership of your Great-3 team %s.

If you know them and want to ACCEPT their request, please go to this address:
%s

If you do want to REJECT them from your team, go to this address:
%s

You can also look at requests on the Great-3 main site:
http://%s

Many thanks,
The Great-3 Team
""" % (team_leader.user.username, user.username, user.email, team, accept_link, reject_link, main_site)
	team_leader.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)


@login_required
def request_join(request, team_id):
	team = Team.objects.get(id=team_id)

	if user_is_member_of_team(request.user, team):
		data = dict(team=team)
		return render(request, "leaderboard/team_request_member.html", data)

	if MembershipRequest.objects.filter(team=team,user=request.user).exists():
		data = dict(team=team)
		return render(request, "leaderboard/team_request_already.html", data)

	membership_request = MembershipRequest(user=request.user, team=team)
	token = membership_request.generate_token()
	membership_request.save()

	#Now send an email request to the team creator
	# Figure out which user to send the email to
	send_request_email(request.user, team, token)

	data = dict(team=team)
	return render(request, "leaderboard/team_request.html", data)

@login_required
def accept(request, token):
	# Also need to check that logged in user is member of requested team!
	try:
		membership_request = MembershipRequest.objects.get(token=token)
	except MembershipRequest.DoesNotExist:
		return render(request, "leaderboard/team_request_fail.html")

	leader_profile = request.user.get_profile()
	try:
		leader_profile.teams.get(id=membership_request.team.id)
	except Team.DoesNotExist:
		return render(request, "leaderboard/not_authorized.html")

	new_member_profile = membership_request.user.get_profile()
	new_member_profile.teams.add(membership_request.team)
	new_member_profile.save()
	membership_request.delete()

	#maybe we should email the user to tell them they have been accepted here?

	return render(request, "leaderboard/team_request_accept.html")

@login_required
def reject(request, token):
	try:
		membership_request = MembershipRequest.objects.get(token=token)
	except MembershipRequest.DoesNotExist:
		return render(request, "leaderboard/team_request_fail.html")

	leader_profile = request.user.get_profile()
	try:
		print leader_profile.teams
		leader_profile.teams.get(id=membership_request.team.id)
	except Team.DoesNotExist:
		return render(request, "leaderboard/not_authorized.html")


	membership_request.delete()
	return render(request, "leaderboard/team_request_reject.html")

